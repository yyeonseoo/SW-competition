"use client";

import { useCallback, useEffect, useState } from "react";
import { getDashboard, getMeta } from "@/lib/api";
import type { ActivityCard, DashboardResponse, MetaResponse } from "@/lib/types";
import AppHeader from "./AppHeader";
import CardList from "./CardList";
import NotificationDrawer from "./NotificationDrawer";
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
  const [profileOpen, setProfileOpen] = useState(false);
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const [showBroadRecommendations, setShowBroadRecommendations] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async (showRefreshing = false) => {
    if (showRefreshing) setRefreshing(true);
    try {
      const nextData = await getDashboard(studentId);
      setData(nextData);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "불러오기에 실패했어요.");
    } finally {
      if (showRefreshing) setRefreshing(false);
    }
  }, [studentId]);

  useEffect(() => {
    getDashboard(studentId)
      .then((nextData) => {
        setData(nextData);
        setError(null);
      })
      .catch((err) =>
        setError(err instanceof Error ? err.message : "불러오기에 실패했어요.")
      );
    getMeta()
      .then(setMeta)
      .catch(() => setMeta(null));
  }, [studentId]);

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
  const relevanceVisible = (card: ActivityCard) =>
    showBroadRecommendations ||
    card.recommendation_score === null ||
    card.recommendation_score >= 40;
  const internalCardsByRelevance = data.internal.cards.filter(relevanceVisible);
  const internalUrgentByRelevance = data.internal.urgent.filter(relevanceVisible);
  const visibleInternalCards =
    internalCategory === "전체"
      ? internalCardsByRelevance
      : internalCardsByRelevance.filter(
          (card) => card.activity_category === internalCategory
        );
  const visibleInternalUrgent =
    internalCategory === "전체"
      ? internalUrgentByRelevance
      : internalUrgentByRelevance.filter(
          (card) => card.activity_category === internalCategory
        );
  const rawExternalCards =
    externalSource === "kw"
      ? data.external.kw_external_cards
      : data.external.linkareer_cards;
  const externalCards = rawExternalCards.filter(relevanceVisible);
  const visibleExternalCards =
    externalCategory !== "전체"
      ? externalCards.filter(
          (card) => card.activity_category === externalCategory
        )
      : externalCards;
  const externalUrgent = data.external.urgent.filter((card) =>
    relevanceVisible(card) &&
    (externalSource === "kw"
      ? card.source === "광운대학교"
      : card.source === "링커리어") &&
    (externalCategory === "전체" ||
      card.activity_category === externalCategory)
  );
  const kwUrgentByRelevance = data.external.urgent.filter(
    (card) => relevanceVisible(card) && card.source === "광운대학교"
  );
  const linkareerUrgentByRelevance = data.external.urgent.filter(
    (card) => relevanceVisible(card) && card.source === "링커리어"
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
    data.external.kw_external_cards.filter(relevanceVisible).length +
    kwUrgentByRelevance.length;
  const linkareerCount =
    data.external.linkareer_cards.filter(relevanceVisible).length +
    linkareerUrgentByRelevance.length;
  const notificationCards = [
    ...data.internal.urgent,
    ...data.external.urgent,
  ];
  const hiddenLowCount = [
    ...data.internal.cards,
    ...data.internal.urgent,
    ...data.external.kw_external_cards,
    ...data.external.linkareer_cards,
    ...data.external.urgent,
  ].filter(
    (card) =>
      card.recommendation_score !== null && card.recommendation_score < 40
  ).length;

  return (
    <section className="view">
      <AppHeader
        avatarLabel={avatarLabel}
        notificationCount={notificationCards.length}
        onNotificationsClick={() => {
          setProfileOpen(false);
          setNotificationsOpen(true);
        }}
        onProfileClick={() => {
          setNotificationsOpen(false);
          setProfileOpen(true);
        }}
      />
      <main className="dashboard-main">
        <header className="dashboard-heading">
          <span>맞춤 공고</span>
          <h1>오늘 확인할 새로운 소식</h1>
          <p>
            {data.student.department} {data.student.grade}학년의 조건과 관심분야를
            바탕으로 정리했어요.
          </p>
        </header>
        <TabsBar
          active={tab}
          internalCount={internalCardsByRelevance.length + internalUrgentByRelevance.length}
          externalCount={
            data.external.kw_external_cards.filter(relevanceVisible).length +
            data.external.linkareer_cards.filter(relevanceVisible).length +
            data.external.urgent.filter(relevanceVisible).length
          }
          onChange={(nextTab) => {
            setTab(nextTab);
            setShowBroadRecommendations(false);
          }}
        />

        <div className="content">
        {tab === "internal" && (
          <div className="tab-panel active">
            <CategoryTabs
              cards={internalCardsByRelevance}
              urgentCards={internalUrgentByRelevance}
              active={internalCategory}
              onChange={setInternalCategory}
              label="교내 프로그램 활동 유형"
            />
            {hiddenLowCount > 0 && (
              <button
                type="button"
                className="broader-results-toggle"
                onClick={() => setShowBroadRecommendations((value) => !value)}
              >
                {showBroadRecommendations
                  ? "관련도 낮은 공고 숨기기"
                  : "추천 범위 넓게 보기"}
              </button>
            )}
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
                  setShowBroadRecommendations(false);
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
                  setShowBroadRecommendations(false);
                }}
              >
                링커리어 <span>{linkareerCount}</span>
              </button>
            </div>

            <CategoryTabs
              cards={externalCards}
              urgentCards={
                externalSource === "kw"
                  ? kwUrgentByRelevance
                  : linkareerUrgentByRelevance
              }
              active={externalCategory}
              onChange={setExternalCategory}
              label={`${
                externalSource === "kw" ? "광운대 공지" : "링커리어"
              } 활동 유형`}
            />
            {hiddenLowCount > 0 && (
              <button
                type="button"
                className="broader-results-toggle"
                onClick={() => setShowBroadRecommendations((value) => !value)}
              >
                {showBroadRecommendations
                  ? "관련도 낮은 공고 숨기기"
                  : "추천 범위 넓게 보기"}
              </button>
            )}

            <UrgentSection cards={externalUrgent} />

            {visibleExternalCards.length === 0 ? (
              <CardList
                cards={[]}
                emptyText="조건에 맞는 교외활동이 아직 없어요."
              />
            ) : externalCategory === "전체" ? (
              <section className="category-section">
                <div className="section-head">
                  <h3>전체 공고</h3>
                  <span className="meta">추천순</span>
                </div>
                <CardList cards={visibleExternalCards} />
              </section>
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
      </main>

      {refreshing && (
        <div className="recommendation-loading" role="status" aria-live="polite">
          <div className="recommendation-loading-card">
            <span className="loading-spinner" aria-hidden="true" />
            <div>
              <strong>수정사항을 반영하고 있어요</strong>
              <p>새 프로필 기준으로 추천 공고를 다시 정리하는 중이에요.</p>
            </div>
          </div>
        </div>
      )}

      <ProfileBar
        student={data.student}
        open={profileOpen}
        onClose={() => setProfileOpen(false)}
        onEditClick={() => {
          setProfileOpen(false);
          setModalOpen(true);
        }}
      />
      <NotificationDrawer
        open={notificationsOpen}
        cards={notificationCards}
        onClose={() => setNotificationsOpen(false)}
      />

      {modalOpen && (
        <ProfileEditModal
          student={data.student}
          meta={meta}
          onClose={() => setModalOpen(false)}
          onSaved={async () => {
            await load(true);
            setModalOpen(false);
          }}
        />
      )}
    </section>
  );
}
