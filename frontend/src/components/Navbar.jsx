import { NavLink } from 'react-router-dom'
import styles from './Navbar.module.css'

export default function Navbar() {
  return (
    <nav className={styles.nav}>
      <NavLink to="/" className={styles.brand}>
        <span className={styles.brandText}>Seattle Sports</span>
        <span className={styles.brandSub}>Tracker</span>
      </NavLink>

      <div className={styles.links}>
        <NavLink
          to="/"
          end
          className={({ isActive }) =>
            `${styles.link} ${isActive ? styles.active : ''}`
          }
        >
          Home
        </NavLink>
        <NavLink
          to="/seahawks"
          className={({ isActive }) =>
            `${styles.link} ${isActive ? styles.activeSeahawks : ''}`
          }
        >
          <span className={styles.dot} style={{ background: 'var(--seahawks-green)' }} />
          Seahawks
        </NavLink>
        <NavLink
          to="/mariners"
          className={({ isActive }) =>
            `${styles.link} ${isActive ? styles.activeMariners : ''}`
          }
        >
          <span className={styles.dot} style={{ background: 'var(--mariners-teal)' }} />
          Mariners
        </NavLink>
        <NavLink
          to="/kraken"
          className={({ isActive }) =>
            `${styles.link} ${isActive ? styles.activeKraken : ''}`
          }
        >
          <span className={styles.dot} style={{ background: '#99D9D9' }} />
          Kraken
        </NavLink>
        <NavLink
          to="/analytics/nfl-injuries"
          className={({ isActive }) =>
            `${styles.link} ${isActive ? styles.activeAnalytics : ''}`
          }
        >
          <span className={styles.dot} style={{ background: '#69BE28' }} />
          Analytics
        </NavLink>
      </div>
    </nav>
  )
}
