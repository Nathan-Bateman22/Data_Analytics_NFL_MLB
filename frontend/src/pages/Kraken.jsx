import useRoster from '../hooks/useRoster'
import TeamHeader from '../components/TeamHeader'
import RosterGrid from '../components/RosterGrid'
import LoadingSpinner from '../components/LoadingSpinner'
import styles from './TeamPage.module.css'

export default function Kraken() {
  const { data, loading, error } = useRoster('/api/kraken/roster/')

  if (loading) return <LoadingSpinner color="#99D9D9" message="Loading Kraken roster..." />
  if (error) return <div className={styles.error}>Failed to load roster: {error}</div>

  return (
    <div className={styles.page}>
      <TeamHeader team={data.team} total={data.total} sport="NHL · Seattle Kraken" />
      <RosterGrid
        players={data.players}
        theme={data.team}
        playerLinkFn={p => `/kraken/player/${p.id}`}
      />
    </div>
  )
}
