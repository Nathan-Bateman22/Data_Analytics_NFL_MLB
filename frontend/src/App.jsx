import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Navbar from './components/Navbar'
import Home from './pages/Home'
import Seahawks from './pages/Seahawks'
import Mariners from './pages/Mariners'
import Kraken from './pages/Kraken'
import PlayerDetail from './pages/PlayerDetail'
import InjuryAnalysis from './pages/InjuryAnalysis'
import PitchingTemps from './pages/PitchingTemps'
import './App.css'

export default function App() {
  return (
    <BrowserRouter>
      <Navbar />
      <main className="main-content">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/seahawks" element={<Seahawks />} />
          <Route path="/seahawks/player/:id" element={<PlayerDetail />} />
          <Route path="/mariners" element={<Mariners />} />
          <Route path="/mariners/player/:id" element={<PlayerDetail />} />
          <Route path="/kraken" element={<Kraken />} />
          <Route path="/kraken/player/:id" element={<PlayerDetail />} />
          <Route path="/analytics/nfl-injuries" element={<InjuryAnalysis />} />
          <Route path="/analytics/mariners-pitching-temps" element={<PitchingTemps />} />
        </Routes>
      </main>
    </BrowserRouter>
  )
}
