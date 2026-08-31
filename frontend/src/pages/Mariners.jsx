import useRoster from '../hooks/useRoster'
import TeamHeader from '../components/TeamHeader'
import RosterGrid from '../components/RosterGrid'
import LoadingSpinner from '../components/LoadingSpinner'
import styles from './TeamPage.module.css'

export default function Mariners() {
  const { data, loading, error } = useRoster('/api/mariners/roster/')

  if (loading) return <LoadingSpinner color="#005C5C" message="Loading Mariners roster..." />
  if (error) return <div className={styles.error}>Failed to load roster: {error}</div>

  return (
    <div className={styles.page}>
      <TeamHeader team={data.team} total={data.total} sport="MLB · Seattle Mariners" />
      <RosterGrid
        players={data.players}
        theme={data.team}
        playerLinkFn={p => `/mariners/player/${p.id}`}
      />
    </div>
  )
}
