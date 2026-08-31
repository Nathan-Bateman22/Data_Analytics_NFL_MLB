import styles from './StatsTable.module.css'

export default function StatsTable({ table, theme }) {
  return (
    <section className={styles.section}>
      <h2 className={styles.title} style={{ color: theme.secondary }}>
        {table.name}
      </h2>

      <div className={styles.tableWrap}>
        <table className={styles.table}>
          <thead>
            <tr>
              {table.headers.map(h => (
                <th
                  key={h}
                  className={h === 'Season' ? styles.thSeason : styles.th}
                  style={h === 'Season' ? {} : { '--hdr-color': theme.secondary }}
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {table.seasons.map(row => (
              <tr key={row.year} className={styles.row}>
                <td className={styles.tdSeason}>{row.year}</td>
                {row.values.map((v, i) => (
                  <td key={i} className={styles.td}>{v}</td>
                ))}
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr className={styles.careerRow} style={{ '--career-color': theme.secondary }}>
              <td className={styles.tdCareerLabel}>Career</td>
              {table.career.map((v, i) => (
                <td key={i} className={styles.tdCareer}>{v}</td>
              ))}
            </tr>
          </tfoot>
        </table>
      </div>
    </section>
  )
}
