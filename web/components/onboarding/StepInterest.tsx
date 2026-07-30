"use client";

interface Props {
  allInterests: string[];
  selected: string[];
  onToggle: (tag: string) => void;
  allActivityTypes: string[];
  selectedActivityTypes: string[];
  onToggleActivityType: (tag: string) => void;
  notifyOptIn: boolean;
  onToggleNotify: () => void;
  email: string;
  onChangeEmail: (v: string) => void;
  preferenceText: string;
  onChangePreferenceText: (v: string) => void;
}

export default function StepInterest({
  allInterests,
  selected,
  onToggle,
  allActivityTypes,
  selectedActivityTypes,
  onToggleActivityType,
  notifyOptIn,
  onToggleNotify,
  email,
  onChangeEmail,
  preferenceText,
  onChangePreferenceText,
}: Props) {
  return (
    <>
      <h1>어떤 분야와 활동을 좋아하세요?</h1>
      <p className="lead">관심 주제와 선호하는 활동 형태를 나눠서 골라주세요.</p>

      <div className="section-subtitle">관심 주제</div>
      <div className="field">
        <div className="tag-picker">
          {allInterests.map((tag) => (
            <span
              key={tag}
              className={`tag${selected.includes(tag) ? " on" : ""}`}
              onClick={() => onToggle(tag)}
            >
              {tag}
            </span>
          ))}
        </div>
        <div className="hint">
          {selected.length}개 선택됨 · 언제든 프로필에서 변경 가능
        </div>
      </div>

      <div className="section-subtitle">선호 활동 유형</div>
      <div className="field">
        <div className="tag-picker">
          {allActivityTypes.map((tag) => (
            <span
              key={tag}
              className={`tag${selectedActivityTypes.includes(tag) ? " on" : ""}`}
              onClick={() => onToggleActivityType(tag)}
            >
              {tag}
            </span>
          ))}
        </div>
        <div className="hint">
          {selectedActivityTypes.length}개 선택됨 · 분야와 별도로 활동 방식을 반영해요
        </div>
      </div>

      <div className="section-subtitle">원하는 활동을 문장으로 설명하기 (선택)</div>
      <div className="field">
        <textarea
          className="input preference-input"
          value={preferenceText}
          maxLength={500}
          onChange={(e) => onChangePreferenceText(e.target.value)}
          placeholder="예: AI 프로젝트나 해커톤에 참여해서 실무 경험과 포트폴리오를 쌓고 싶어요."
        />
        <div className="hint">
          자연어로 적어주면 공고 내용과 의미가 비슷한 활동을 먼저 추천해요.
        </div>
      </div>

      <div className="section-subtitle">알림</div>
      <div className="field">
        <div className="toggle-row">
          <div className="label">
            <b>새 맞춤 공고 이메일 알림</b>
            <small>하루 1회 요약 · 새 공고가 있을 때만 발송</small>
          </div>
          <div
            className={`toggle${notifyOptIn ? " on" : ""}`}
            onClick={onToggleNotify}
          />
        </div>
      </div>
      <div className="field">
        <label>이메일 주소</label>
        <input
          className="input"
          type="email"
          value={email}
          onChange={(e) => onChangeEmail(e.target.value)}
          placeholder="you@kw.ac.kr"
        />
      </div>
    </>
  );
}
