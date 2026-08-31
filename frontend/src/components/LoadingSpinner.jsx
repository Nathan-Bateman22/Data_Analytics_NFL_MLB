import styles from './LoadingSpinner.module.css'

export default function LoadingSpinner({ color = '#69BE28', message = 'Loading roster...' }) {
  return (
    <div className={styles.wrap}>
      <div className={styles.ring} style={{ '--color': color }} />
      <p className={styles.msg}>{message}</p>
    </div>
  )
}
