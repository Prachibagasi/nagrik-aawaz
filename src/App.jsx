import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { ThemeProvider } from './context/ThemeContext'
import { AuthProvider } from './context/AuthContext'
import Layout from './components/Layout'
import RequireAuth from './components/RequireAuth'
import RequireDesk from './components/RequireDesk'
import HomePage from './pages/HomePage'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import TrackPage from './pages/TrackPage'
import DashboardPage from './pages/DashboardPage'
import MyComplaintsPage from './pages/MyComplaintsPage'
import NewComplaintPage from './pages/NewComplaintPage'
import ComplaintDetailPage from './pages/ComplaintDetailPage'
import ProfilePage from './pages/ProfilePage'
import AdminDeskPage from './pages/AdminDeskPage'
import VoiceReportPage from './pages/VoiceReportPage'
import FaqPage from './pages/FaqPage'
import ClusterPage from './pages/ClusterPage'
import SentimentAnalyticsPage from './pages/SentimentAnalyticsPage'

export default function App() {
  return (
    <BrowserRouter>
      <ThemeProvider>
        <AuthProvider>
          <Routes>
            <Route element={<Layout />}>
              <Route path="/" element={<HomePage />} />
              <Route path="/login" element={<LoginPage />} />
              <Route path="/register" element={<RegisterPage />} />
              <Route path="/track" element={<TrackPage />} />
              <Route path="/faq" element={<FaqPage />} />
              <Route element={<RequireAuth />}>
                <Route path="/dashboard" element={<DashboardPage />} />
                <Route path="/complaints" element={<MyComplaintsPage />} />
                <Route path="/complaints/new" element={<NewComplaintPage />} />
                <Route path="/complaints/:id" element={<ComplaintDetailPage />} />
                <Route path="/profile" element={<ProfilePage />} />
                <Route path="/voice" element={<VoiceReportPage />} />
                <Route path="/clusters/:clusterKey" element={<ClusterPage />} />
                <Route element={<RequireDesk />}>
                  <Route path="/desk" element={<AdminDeskPage />} />
                  <Route path="/insights/sentiment" element={<SentimentAnalyticsPage />} />
                </Route>
              </Route>
            </Route>
          </Routes>
        </AuthProvider>
      </ThemeProvider>
    </BrowserRouter>
  )
}
