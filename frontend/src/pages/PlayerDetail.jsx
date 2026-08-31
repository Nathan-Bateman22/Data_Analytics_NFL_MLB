import { useState } from 'react'
import { useParams, useLocation, Link } from 'react-router-dom'
import useRoster from '../hooks/useRoster'
import StatsTable from '../components/StatsTable'
import LoadingSpinner from '../components/LoadingSpinner'
import styles from './PlayerDetail.module.css'

const PLACEHOLDER = 'https://a.espncdn.com/i/headshots/nophoto.png'

const DEFAULT_THEMES = {
  seahawks: { primary: '#002244', secondary: '#69BE28', accent: '#A5ACAF' },
  mariners: { primary: '#0C2C56', secondary: '#005C5C', accent: '#C4CED4' },
  kraken:   { primary: '#001628', secondary: '#99D9D9', accent: '#C8102E' },
}

const TEAM_LABELS = {
  seahawks: 'Seahawks Roster',
  mariners: 'Mariners Roster',
  kraken:   'Kraken Roster',
}

export default function PlayerDetail() {
  const { id } = useParams()
  const location = useLocation()

  // Derive team from URL path so no extra state plumbing is needed
  const team = location.pathname.startsWith('/mariners')
    ? 'mariners'
    : location.pathname.startsWith('/kraken')
    ? 'kraken'
    : 'seahawks'
  const theme = location.state?.theme || DEFAULT_THEMES[team]

  const { data, loading, error } = useRoster(`/api/${team}/players/${id}/stats/`)
  const [imgSrc, setImgSrc] = useState(null)

  if (loading) return <LoadingSpinner color={theme.secondary} message="Loading player stats..." />
  if (error) return (
    <div className={styles.errorWrap}>
      <p className={styles.error}>Failed to load player stats: {error}</p>
      <Link to={`/${team}`} className={styles.back}>← Back to roster</Link>
    </div>
  )

  const { player, positionGroup, tables } = data
  const headshot = imgSrc === 'err' ? PLACEHOLDER : (player.headshot || PLACEHOLDER)

  return (
    <div className={styles.page}>
      <Link to={`/${team}`} className={styles.back} style={{ color: theme.secondary }}>
        ← {TEAM_LABELS[team]}
      </Link>

      <div className={styles.hero} style={{ '--primary': theme.primary, '--secondary': theme.secondary }}>
        <div className={styles.heroBg} />
        <div className={styles.heroGlow} />
        <div className={styles.heroContent}>
          <div className={styles.headshotWrap} style={{ background: theme.primary }}>
            <img
              src={headshot}
              alt={player.fullName}
              className={styles.headshot}
              onError={() => setImgSrc('err')}
            />
          </div>

          <div className={styles.heroInfo}>
            <div className={styles.jerseyBadge} style={{ color: theme.secondary }}>
              #{player.jersey}
            </div>
            <h1 className={styles.playerName}>{player.fullName}</h1>
            <div className={styles.posLine}>
              <span
                className={styles.posBadge}
                style={{
                  color: theme.secondary,
                  borderColor: `${theme.secondary}40`,
                  background: `${theme.secondary}15`,
                }}
              >
                {player.position}
              </span>
              <span className={styles.posGroup}>{positionGroup}</span>
            </div>

            <div className={styles.bioGrid}>
              {player.height && <BioStat label="Height" value={player.height} />}
              {player.weight && <BioStat label="Weight" value={player.weight} />}
              {player.age && <BioStat label="Age" value={player.age} />}
              {player.experience !== null && player.experience !== undefined && (
                <BioStat
                  label="Experience"
                  value={player.experience === 0 ? 'Rookie' : `${player.experience} yr`}
                />
              )}
              {player.college && <BioStat label="College" value={player.college} />}
              {player.birthPlace && <BioStat label="Hometown" value={player.birthPlace} />}
            </div>
          </div>
        </div>
      </div>

      <div className={styles.statsSection}>
        {tables.length === 0 ? (
          <div className={styles.noStats}>
            Individual statistics are not tracked for this position.
          </div>
        ) : (
          <div className={styles.tables}>
            {tables.map(table => (
              <StatsTable key={table.name} table={table} theme={theme} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function BioStat({ label, value }) {
  return (
    <div className={styles.bioStat}>
      <span className={styles.bioLabel}>{label}</span>
      <span className={styles.bioValue}>{value}</span>
    </div>
  )
}
