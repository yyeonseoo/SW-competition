"use client";

import CustomSelect from "@/components/ui/CustomSelect";

interface Props {
  regions: Record<string, string[]>;
  sido: string;
  sigungu: string;
  onChangeSido: (v: string) => void;
  onChangeSigungu: (v: string) => void;
  isInternational: boolean | null;
  onChangeInternational: (value: boolean) => void;
}

export default function StepRegion({
  regions,
  sido,
  sigungu,
  onChangeSido,
  onChangeSigungu,
  isInternational,
  onChangeInternational,
}: Props) {
  const sigunguOptions = sido ? regions[sido] ?? [] : [];

  return (
    <>
      <h1>거주 및 학생 정보를 알려주세요</h1>
      <p className="lead">지역 제한과 국제학생 전용 공고를 정확하게 구분해요.</p>

      <div className="field">
        <label>시·도 · 필수</label>
        <CustomSelect
          value={sido}
          placeholder="시·도를 선택하세요"
          options={Object.keys(regions).map((name) => ({ value: name, label: name }))}
          onChange={onChangeSido}
        />
      </div>
      <div className="field">
        <label>시·군·구 · 필수</label>
        <CustomSelect
          value={sigungu}
          placeholder="시·군·구를 선택하세요"
          disabled={!sido}
          options={sigunguOptions.map((name) => ({ value: name, label: name }))}
          onChange={onChangeSigungu}
        />
      </div>
      <div className="field">
        <label>국제학생 여부 · 필수</label>
        <div className="choice-cards">
          <button
            type="button"
            className={`choice-card${isInternational === false ? " selected" : ""}`}
            onClick={() => onChangeInternational(false)}
          >
            국내 학생
          </button>
          <button
            type="button"
            className={`choice-card${isInternational === true ? " selected" : ""}`}
            onClick={() => onChangeInternational(true)}
          >
            국제학생
          </button>
        </div>
      </div>
    </>
  );
}
