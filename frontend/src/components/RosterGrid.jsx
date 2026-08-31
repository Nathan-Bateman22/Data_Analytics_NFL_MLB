import { useState, useMemo } from 'react'
import PlayerCard from './PlayerCard'
import styles from './RosterGrid.module.css'

export default function RosterGrid({ players, theme, playerLinkFn }) {
  const [search, setSearch] = useState('')
  const [posFilter, setPosFilter] = useState('All')
  const [sort, setSort] = useState('jersey')

  const positions = useMemo(() => {
    const set = new Set(players.map(p => p.position).filter(Boolean))
    return ['All', ...Array.from(set).sort()]
  }, [players])

  const filtered = useMemo(() => {
    let list = players
    if (search.trim()) {
      const q = search.toLowerCase()
      list = list.filter(p =>
        p.fullName.toLowerCase().includes(q) ||
        p.position.toLowerCase().includes(q) ||
        String(p.jersey).includes(q)
      )
    }
    if (posFilter !== 'All') {
      list = list.filter(p => p.position === posFilter)
    }
    return [...list].sort((a, b) => {
      if (sort === 'jersey') return (parseInt(a.jersey) || 99) - (parseInt(b.jersey) || 99)
      if (sort === 'name') return a.lastName.localeCompare(b.lastName)
      return 0
    })
  }, [players, search, posFilter, sort])

  return (
    <div className={styles.root}>
      <div className={styles.controls}>
        <input
          className={styles.search}
          type="text"
          placeholder="Search players..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          style={{ '--focus-color': theme.secondary }}
        />

        <div className={styles.filters}>
          {positions.map(pos => (
            <button
              key={pos}
              className={`${styles.pill} ${posFilter === pos ? styles.pillActive : ''}`}
              style={posFilter === pos ? { background: theme.secondary, color: '#000', borderColor: theme.secondary } : {}}
              onClick={() => setPosFilter(pos)}
            >
              {pos}
            </button>
          ))}
        </div>

        <div className={styles.sortRow}>
          <span className={styles.sortLabel}>Sort:</span>
          <button
            className={`${styles.sortBtn} ${sort === 'jersey' ? styles.sortActive : ''}`}
            onClick={() => setSort('jersey')}
            style={sort === 'jersey' ? { color: theme.secondary } : {}}
          >
            # Jersey
          </button>
          <button
            className={`${styles.sortBtn} ${sort === 'name' ? styles.sortActive : ''}`}
            onClick={() => setSort('name')}
            style={sort === 'name' ? { color: theme.secondary } : {}}
          >
            Name
          </button>
        </div>

        <span className={styles.count}>{filtered.length} players</span>
      </div>

      {filtered.length === 0 ? (
        <div className={styles.empty}>No players match your search.</div>
      ) : (
        <div className={styles.grid}>
          {filtered.map(player => (
            <PlayerCard
              key={player.id}
              player={player}
              theme={theme}
              to={playerLinkFn ? playerLinkFn(player) : undefined}
            />
          ))}
        </div>
      )}
    </div>
  )
}
