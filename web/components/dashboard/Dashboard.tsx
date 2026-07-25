"use client";

import { useCallback, useEffect, useState } from "react";
import { getDashboard, getMeta } from "@/lib/api";
import type { DashboardResponse, MetaResponse } from "@/lib/types";
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

export default function Dashboard({ studentId, onReset }: Props) {
  const [data, setData] = useState<DashboardResponse | null>(null);
  const [meta, setMeta] = useState<MetaResponse | null>(null);
  const [tab, setTab] = useState<"internal" | "external">("internal");
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

  return (
    <section className="view">
      <AppHeader avatarLabel={avatarLabel} />
      <ProfileBar
        student={data.student}
        newTodayCount={data.new_today_count}
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
            <UrgentSection cards={data.internal.urgent} />
            <div className="section-head" style={{ marginTop: 32 }}>
              <h3>전체 공고</h3>
              <span className="meta">최신순</span>
            </div>
            <CardList
              cards={data.internal.cards}
              emptyText="조건에 맞는 교내 공고가 아직 없어요."
            />
          </div>
        )}

        {tab === "external" && (
          <div className="tab-panel active">
            <UrgentSection cards={data.external.urgent} />

            <div className="subsection">
              광운대 공지 · 외부 프로그램
              <span className="subhint">지역·관심분야가 겹치는 항목</span>
            </div>
            <CardList
              cards={data.external.kw_external_cards}
              emptyText="조건에 맞는 외부 프로그램이 아직 없어요."
            />

            <div className="subsection" style={{ marginTop: 32 }}>
              링커리어 · 인기 공고
              <span className="subhint">관심분야 기준 · 최대 6개</span>
            </div>
            <CardList
              cards={data.external.linkareer_cards}
              emptyText="조건에 맞는 링커리어 공고가 아직 없어요."
            />
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
