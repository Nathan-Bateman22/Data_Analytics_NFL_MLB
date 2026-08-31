import { useState } from 'react'
import { Link } from 'react-router-dom'
import styles from './PlayerCard.module.css'

const PLACEHOLDER = 'https://a.espncdn.com/i/headshots/nophoto.png'

export default function PlayerCard({ player, theme, to }) {
  const [imgSrc, setImgSrc] = useState(player.headshot || PLACEHOLDER)

  const inner = (
    <>
      <div className={styles.headshotWrap} style={{ background: theme.primary }}>
        <img
          src={imgSrc}
          alt={player.fullName}
          className={styles.headshot}
          onError={() => setImgSrc(PLACEHOLDER)}
          loading="lazy"
        />
        <span className={styles.jersey} style={{ color: theme.secondary }}>
          #{player.jersey}
        </span>
      </div>

      <div className={styles.info}>
        <div className={styles.name}>{player.fullName}</div>
        <div className={styles.position} style={{ color: theme.secondary }}>
          {player.positionGroup ? `${player.position} · ${player.positionGroup}` : player.position}
        </div>

        <div className={styles.meta}>
          {player.height && <Stat label="HT" value={player.height} />}
          {player.weight && <Stat label="WT" value={player.weight} />}
          {player.age && <Stat label="AGE" value={player.age} />}
          {player.experience !== null && player.experience !== undefined && (
            <Stat label="EXP" value={player.experience === 0 ? 'Rookie' : `${player.experience}yr`} />
          )}
        </div>

        {player.college && <div className={styles.college}>{player.college}</div>}
        {player.birthPlace && <div className={styles.birthplace}>{player.birthPlace}</div>}

        {to && (
          <div className={styles.viewStats} style={{ color: theme.secondary }}>
            View stats →
          </div>
        )}
      </div>
    </>
  )

  if (to) {
    return (
      <Link
        to={to}
        state={{ theme }}
        className={`${styles.card} ${styles.cardLink}`}
        style={{ '--accent': theme.secondary }}
      >
        {inner}
      </Link>
    )
  }

  return (
    <div className={styles.card} style={{ '--accent': theme.secondary }}>
      {inner}
    </div>
  )
}

function Stat({ label, value }) {
  return (
    <div className={styles.stat}>
      <span className={styles.statLabel}>{label}</span>
      <span className={styles.statValue}>{value}</span>
    </div>
  )
}
