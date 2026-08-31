import { Link } from 'react-router-dom'
import styles from './Home.module.css'

const TEAMS = [
  {
    key: 'seahawks',
    path: '/seahawks',
    name: 'Seattle Seahawks',
    league: 'NFL',
    primary: '#002244',
    secondary: '#69BE28',
    logo: 'https://a.espncdn.com/i/teamlogos/nfl/500/sea.png',
    desc: 'Active roster · Player profiles',
  },
  {
    key: 'mariners',
    path: '/mariners',
    name: 'Seattle Mariners',
    league: 'MLB',
    primary: '#0C2C56',
    secondary: '#005C5C',
    logo: 'https://a.espncdn.com/i/teamlogos/mlb/500/sea.png',
    desc: 'Active roster · Player profiles',
  },
  {
    key: 'kraken',
    path: '/kraken',
    name: 'Seattle Kraken',
    league: 'NHL',
    primary: '#001628',
    secondary: '#99D9D9',
    logo: 'https://a.espncdn.com/i/teamlogos/nhl/500/sea.png',
    desc: 'Active roster · Player profiles',
  },
]

export default function Home() {
  return (
    <div className={styles.page}>
      <div className={styles.hero}>
        <div className={styles.heroEyebrow}>Welcome to</div>
        <h1 className={styles.heroTitle}>Seattle Sports Tracker</h1>
        <p className={styles.heroSub}>
          Rosters, player profiles, and in-depth stats for your favorite Seattle teams.
        </p>
      </div>

      <div className={styles.cards}>
        {TEAMS.map(team => (
          <Link
            key={team.key}
            to={team.path}
            className={styles.card}
            style={{ '--primary': team.primary, '--secondary': team.secondary }}
          >
            <div className={styles.cardBg} />
            <div className={styles.cardGlow} />
            <div className={styles.cardContent}>
              <img
                src={team.logo}
                alt={team.name}
                className={styles.cardLogo}
                onError={e => { e.target.style.display = 'none' }}
              />
              <div className={styles.cardText}>
                <span className={styles.cardLeague}>{team.league}</span>
                <span className={styles.cardName}>{team.name}</span>
                <span className={styles.cardDesc}>{team.desc}</span>
              </div>
              <span className={styles.cardArrow}>→</span>
            </div>
          </Link>
        ))}
      </div>

      <div className={styles.analyticsSection}>
        <h2 className={styles.analyticsTitle}>Advanced Analytics</h2>
        <div className={styles.analyticsCards}>
          <Link to="/analytics/nfl-injuries" className={styles.analyticsCard}>
            <div className={styles.analyticsCardBadge}>NFL · Surface Analysis</div>
            <div className={styles.analyticsCardName}>Injury Rates: Grass vs. Turf</div>
            <div className={styles.analyticsCardDesc}>
              Non-contact vs. contact injury rates by surface type, with chi-square testing,
              rate ratios, season trends, and position breakdowns.
            </div>
            <div className={styles.analyticsCardArrow}>Explore →</div>
          </Link>
          <Link to="/analytics/mariners-pitching-temps" className={styles.analyticsCard}>
            <div className={styles.analyticsCardBadge}>MLB · Environmental Analysis</div>
            <div className={styles.analyticsCardName}>Starting Pitching by Temperature</div>
            <div className={styles.analyticsCardDesc}>
              How game-day temperature affects Mariners starter performance — ERA, WHIP, K/9
              by temperature band, roof vs. outdoor splits, and per-pitcher breakdowns.
            </div>
            <div className={styles.analyticsCardArrow}>Explore →</div>
          </Link>
        </div>
      </div>
    </div>
  )
}
