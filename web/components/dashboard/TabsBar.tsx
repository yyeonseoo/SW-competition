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
    <div className="tabs-bar">
      <div
        className={`tab${active === "internal" ? " on" : ""}`}
        onClick={() => onChange("internal")}
      >
        교내 프로그램 <span className="count">{internalCount}</span>
      </div>
      <div
        className={`tab${active === "external" ? " on" : ""}`}
        onClick={() => onChange("external")}
      >
        교외활동 <span className="count">{externalCount}</span>
      </div>
    </div>
  );
}
