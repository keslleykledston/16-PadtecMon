import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Sites from './pages/Sites'
import Cards from './pages/Cards'
import CardDetail from './pages/CardDetail'
import Alarms from './pages/Alarms'
import Config from './pages/Config'

function App() {
  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/sites" element={<Sites />} />
          <Route path="/cards" element={<Cards />} />
          <Route path="/cards/:cardSerial" element={<CardDetail />} />
          <Route path="/alarms" element={<Alarms />} />
          <Route path="/config" element={<Config />} />
        </Routes>
      </Layout>
    </Router>
  )
}

export default App

