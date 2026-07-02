import { Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import Search from './pages/Search';
import Watchlist from './pages/Watchlist';
import Library from './pages/Library';
import Requests from './pages/Requests';
import Settings from './pages/Settings';
import Shows from './pages/Shows';
import Movies from './pages/Movies';
import AutoApprove from './pages/AutoApprove';
import Blacklist from './pages/Blacklist';
import Subtitles from './pages/Subtitles';
import Logs from './pages/Logs';
import Login from './pages/Login';
import ProfileSelect from './pages/ProfileSelect';

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/profiles" element={<ProfileSelect />} />
      <Route element={<Layout />}>
        <Route index element={<Navigate to="/movies" replace />} />
        <Route path="library" element={<Library />} />
        <Route path="watchlist" element={<Watchlist />} />
        <Route path="search" element={<Search />} />
        <Route path="shows" element={<Shows />} />
        <Route path="movies" element={<Movies />} />
        <Route path="auto-approve" element={<AutoApprove />} />
        <Route path="blacklist" element={<Blacklist />} />
        <Route path="subtitles" element={<Subtitles />} />
        <Route path="logs" element={<Logs />} />
        <Route path="requests" element={<Requests />} />
        <Route path="wanted" element={<Navigate to="/requests" replace />} />
        <Route path="settings" element={<Settings />} />
        <Route path="admin" element={
          <iframe src="/admin?embed=1" className="w-full border-0" style={{ height: 'calc(100vh - 57px)' }} />
        } />
        <Route path="manual" element={
          <iframe src="/docs/install-guide.html" className="w-full border-0" style={{ height: 'calc(100vh - 57px)' }} />
        } />
        <Route path="*" element={<div className="text-center py-16 text-muted">Page not found</div>} />
      </Route>
    </Routes>
  );
}
