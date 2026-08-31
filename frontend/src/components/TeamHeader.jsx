import styles from './TeamHeader.module.css'

export default function TeamHeader({ team, total, sport }) {
  return (
    <div
      className={styles.header}
      style={{
        '--primary': team.primary,
        '--secondary': team.secondary,
        '--accent': team.accent,
      }}
    >
      <div className={styles.gradient} />
      <div className={styles.content}>
        <img
          src={team.logo}
          alt={`${team.name} logo`}
          className={styles.logo}
          onError={e => { e.target.style.display = 'none' }}
        />
        <div className={styles.text}>
          <div className={styles.sport}>{sport}</div>
          <h1 className={styles.name}>{team.name}</h1>
          <div className={styles.meta}>
            <span className={styles.badge} style={{ color: team.secondary, borderColor: `${team.secondary}40`, background: `${team.secondary}15` }}>
              Active Roster
            </span>
            <span className={styles.total}>{total} Players</span>
          </div>
        </div>
      </div>
    </div>
  )
}
