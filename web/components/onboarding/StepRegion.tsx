"use client";

interface Props {
  regions: Record<string, string[]>;
  sido: string;
  sigungu: string;
  onChangeSido: (v: string) => void;
  onChangeSigungu: (v: string) => void;
  isInternational: boolean;
  onToggleInternational: () => void;
}

export default function StepRegion({
  regions,
  sido,
  sigungu,
  onChangeSido,
  onChangeSigungu,
  isInternational,
  onToggleInternational,
}: Props) {
  const sigunguOptions = sido ? regions[sido] ?? [] : [];

  return (
    <>
      <h1>어디에 사세요?</h1>
      <p className="lead">지역 장학·프로그램(예: 구리시 청년성장) 매칭에 사용해요.</p>

      <div className="field">
        <div className="toggle-row">
          <div className="label">
            <b>🌐 국제학생(유학생)이에요</b>
            <small>켜면 국제학생 대상 공지(장학금·기숙사·수강신청 안내 등)도 함께 보여드려요</small>
          </div>
          <div
            className={`toggle${isInternational ? " on" : ""}`}
            onClick={onToggleInternational}
          />
        </div>
      </div>

      <div className="field">
        <label>시·도</label>
        <select
          className="select"
          value={sido}
          onChange={(e) => onChangeSido(e.target.value)}
        >
          <option value="">시·도를 선택하세요</option>
          {Object.keys(regions).map((name) => (
            <option key={name} value={name}>
              {name}
            </option>
          ))}
        </select>
      </div>
      <div className="field">
        <label>구/시·군</label>
        <select
          className="select"
          value={sigungu}
          onChange={(e) => onChangeSigungu(e.target.value)}
          disabled={!sido}
        >
          <option value="">구/시·군을 선택하세요</option>
          {sigunguOptions.map((name) => (
            <option key={name} value={name}>
              {name}
            </option>
          ))}
        </select>
      </div>
    </>
  );
}
