"use client";

interface Props {
  active: "internal" | "external";
  internalCount: number;
  externalCount: number;
  onChange: (tab: "internal" | "external") => void;
}

export default function TabsBar({
  active,
  internalCount,
  externalCount,
  onChange,
}: Props) {
  return (
    <div className="tabs-bar" role="tablist" aria-label="공고 범위">
      <button
        type="button"
        role="tab"
        aria-selected={active === "internal"}
        className={`tab${active === "internal" ? " on" : ""}`}
        onClick={() => onChange("internal")}
      >
        교내 프로그램 <span className="count">{internalCount}</span>
      </button>
      <button
        type="button"
        role="tab"
        aria-selected={active === "external"}
        className={`tab${active === "external" ? " on" : ""}`}
        onClick={() => onChange("external")}
      >
        교외활동 <span className="count">{externalCount}</span>
      </button>
    </div>
  );
}
