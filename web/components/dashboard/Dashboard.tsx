"use client";

import { useCallback, useEffect, useState } from "react";
import { getDashboard, getMeta } from "@/lib/api";
import type { ActivityCard, DashboardResponse, MetaResponse } from "@/lib/types";
import AppHeader from "./AppHeader";
import CardList from "./CardList";
import ProfileBar from "./ProfileBar";
import ProfileEditModal from "./ProfileEditModal";
import TabsBar from "./TabsBar";
import UrgentSection from "./UrgentSection";

interface Props {
  studentId: number;
  onReset: () => void;
}

const CATEGORY_ORDER = [
  "공모전",
  "대외활동",
  "교육",
  "인턴·채용",
  "장학·지원",
  "기타",
];

function CategoryTabs({
  cards,
  urgentCards,
  active,
  onChange,
  label,
}: {
  cards: ActivityCard[];
  urgentCards: ActivityCard[];
  active: string;
  onChange: (category: string) => void;
  label: string;
}) {
  const allCards = [...urgentCards, ...cards];
  return (
    <div className="category-tabs" role="tablist" aria-label={label}>
      {["전체", ...CATEGORY_ORDER].map((category) => {
        const count =
          category === "전체"
            ? allCards.length
            : allCards.filter((card) => card.activity_category === category)
                .length;
        return (
          <button
            type="button"
            key={category}
            className={`category-tab${active === category ? " on" : ""}`}
            onClick={() => onChange(category)}
          >
            {category} <span>{count}</span>
          </button>
        );
      })}
    </div>
  );
}

export default function Dashboard({ studentId, onReset }: Props) {
  const [data, setData] = useState<DashboardResponse | null>(null);
  const [meta, setMeta] = useState<MetaResponse | null>(null);
  const [tab, setTab] = useState<"internal" | "external">("internal");
  const [externalSource, setExternalSource] = useState<"kw" | "linkareer">("kw");
  const [internalCategory, setInternalCategory] = useState("전체");
  const [externalCategory, setExternalCategory] = useState("전체");
  const [modalOpen, setModalOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    getDashboard(studentId)
      .then(setData)
      .catch((err) =>
        setError(err instanceof Error ? err.message : "불러오기에 실패했어요.")
      );
  }, [studentId]);

  useEffect(() => {
    load();
    getMeta()
      .then(setMeta)
      .catch(() => setMeta(null));
  }, [load]);

  if (error) {
    return (
      <section className="view">
        <AppHeader avatarLabel="KW" />
        <div className="content">
          <div className="empty">
            {error}
            <div style={{ marginTop: 12 }}>
              <button className="btn btn-ghost" onClick={onReset}>
                처음부터 다시 시작
              </button>
            </div>
          </div>
        </div>
      </section>
    );
  }

  if (!data) {
    return (
      <section className="view">
        <AppHeader avatarLabel="KW" />
        <div className="content">불러오는 중...</div>
      </section>
    );
  }

  const avatarLabel = data.student.department.slice(0, 2);
  const visibleInternalCards =
    internalCategory === "전체"
      ? data.internal.cards
      : data.internal.cards.filter(
          (card) => card.activity_category === internalCategory
        );
  const visibleInternalUrgent =
    internalCategory === "전체"
      ? data.internal.urgent
      : data.internal.urgent.filter(
          (card) => card.activity_category === internalCategory
        );
  const externalCards =
    externalSource === "kw"
      ? data.external.kw_external_cards
      : data.external.linkareer_cards;
  const visibleExternalCards =
    externalCategory !== "전체"
      ? externalCards.filter(
          (card) => card.activity_category === externalCategory
        )
      : externalCards;
  const externalUrgent = data.external.urgent.filter((card) =>
    (externalSource === "kw"
      ? card.source === "광운대학교"
      : card.source === "링커리어") &&
    (externalCategory === "전체" ||
      card.activity_category === externalCategory)
  );
  const groupedExternalCards = CATEGORY_ORDER
    .map((category) => ({
      category,
      cards: visibleExternalCards.filter(
        (card) => card.activity_category === category
      ),
    }))
    .filter((group) => group.cards.length > 0);
  const kwCount =
    data.external.kw_external_cards.length +
    data.external.urgent.filter((card) => card.source === "광운대학교").length;
  const linkareerCount =
    data.external.linkareer_cards.length +
    data.external.urgent.filter((card) => card.source === "링커리어").length;

  return (
    <section className="view">
      <AppHeader avatarLabel={avatarLabel} />
      <ProfileBar
        student={data.student}
        onEditClick={() => setModalOpen(true)}
      />
      <TabsBar
        active={tab}
        internalCount={data.internal.count}
        externalCount={data.external.count}
        onChange={setTab}
      />

      <div className="content">
        {tab === "internal" && (
          <div className="tab-panel active">
            <CategoryTabs
              cards={data.internal.cards}
              urgentCards={data.internal.urgent}
              active={internalCategory}
              onChange={setInternalCategory}
              label="교내 프로그램 활동 유형"
            />
            <UrgentSection cards={visibleInternalUrgent} />
            <div className="section-head" style={{ marginTop: 32 }}>
              <h3>{internalCategory === "전체" ? "전체 공고" : internalCategory}</h3>
              <span className="meta">추천순</span>
            </div>
            <CardList
              cards={visibleInternalCards}
              emptyText="조건에 맞는 교내 공고가 아직 없어요."
            />
          </div>
        )}

        {tab === "external" && (
          <div className="tab-panel active">
            <div className="source-tabs" role="tablist" aria-label="교외활동 출처">
              <button
                type="button"
                className={`source-tab${externalSource === "kw" ? " on" : ""}`}
                onClick={() => {
                  setExternalSource("kw");
                  setExternalCategory("전체");
                }}
              >
                광운대 공지 <span>{kwCount}</span>
              </button>
              <button
                type="button"
                className={`source-tab${externalSource === "linkareer" ? " on" : ""}`}
                onClick={() => {
                  setExternalSource("linkareer");
                  setExternalCategory("전체");
                }}
              >
                링커리어 <span>{linkareerCount}</span>
              </button>
            </div>

            <CategoryTabs
              cards={externalCards}
              urgentCards={data.external.urgent.filter((card) =>
                externalSource === "kw"
                  ? card.source === "광운대학교"
                  : card.source === "링커리어"
              )}
              active={externalCategory}
              onChange={setExternalCategory}
              label={`${
                externalSource === "kw" ? "광운대 공지" : "링커리어"
              } 활동 유형`}
            />

            <UrgentSection cards={externalUrgent} />

            {groupedExternalCards.length === 0 ? (
              <CardList
                cards={[]}
                emptyText="조건에 맞는 교외활동이 아직 없어요."
              />
            ) : (
              groupedExternalCards.map((group) => (
                <section className="category-section" key={group.category}>
                  <div className="section-head">
                    <h3>{group.category}</h3>
                    <span className="meta">{group.cards.length}개</span>
                  </div>
                  <CardList cards={group.cards} />
                </section>
              ))
            )}
          </div>
        )}
      </div>

      {modalOpen && (
        <ProfileEditModal
          student={data.student}
          meta={meta}
          onClose={() => setModalOpen(false)}
          onSaved={() => {
            setModalOpen(false);
            load();
          }}
        />
      )}
    </section>
  );
}
