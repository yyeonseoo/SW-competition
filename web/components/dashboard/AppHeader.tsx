interface Props {
  avatarLabel: string;
  notificationCount?: number;
  onNotificationsClick?: () => void;
  onProfileClick?: () => void;
}

export default function AppHeader({
  avatarLabel,
  notificationCount = 0,
  onNotificationsClick,
  onProfileClick,
}: Props) {
  return (
    <header className="app-header">
      <div className="brand">
        <span className="logo">KW</span>
        <span className="name">KW-LIFE</span>
      </div>
      <nav className="header-nav">
        <a href="#" className="active">
          대시보드
        </a>
        <button type="button" onClick={onNotificationsClick}>
          알림
          {notificationCount > 0 && (
            <span className="nav-count">{notificationCount}</span>
          )}
        </button>
      </nav>
      <div className="header-right">
        <button
          type="button"
          className="avatar"
          aria-label="프로필 열기"
          onClick={onProfileClick}
        >
          {avatarLabel}
        </button>
      </div>
    </header>
  );
}
