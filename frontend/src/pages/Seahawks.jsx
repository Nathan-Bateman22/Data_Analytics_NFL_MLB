import useRoster from '../hooks/useRoster'
import TeamHeader from '../components/TeamHeader'
import RosterGrid from '../components/RosterGrid'
import LoadingSpinner from '../components/LoadingSpinner'
import styles from './TeamPage.module.css'

export default function Seahawks() {
  const { data, loading, error } = useRoster('/api/seahawks/roster/')

  if (loading) return <LoadingSpinner color="#69BE28" message="Loading Seahawks roster..." />
  if (error) return <div className={styles.error}>Failed to load roster: {error}</div>

  return (
    <div className={styles.page}>
      <TeamHeader team={data.team} total={data.total} sport="NFL · Seattle Seahawks" />
      <RosterGrid
        players={data.players}
        theme={data.team}
        playerLinkFn={p => `/seahawks/player/${p.id}`}
      />
    </div>
  )
}
