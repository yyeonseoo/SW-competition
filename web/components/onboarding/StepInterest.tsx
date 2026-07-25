"use client";

interface Props {
  allInterests: string[];
  selected: string[];
  onToggle: (tag: string) => void;
  notifyOptIn: boolean;
  onToggleNotify: () => void;
  email: string;
  onChangeEmail: (v: string) => void;
}

export default function StepInterest({
  allInterests,
  selected,
  onToggle,
  notifyOptIn,
  onToggleNotify,
  email,
  onChangeEmail,
}: Props) {
  return (
    <>
      <h1>어떤 활동에 관심 있으세요?</h1>
      <p className="lead">관심 있는 분야를 골라주세요. 이걸 기준으로 추천해드려요.</p>

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
