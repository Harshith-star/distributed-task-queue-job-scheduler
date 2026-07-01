import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider }  from './context/AuthContext';
import { ProtectedRoute } from './components/ui.jsx';
import Layout             from './components/Layout.jsx';
import Login              from './pages/Login.jsx';
import Register           from './pages/Register.jsx';
import Dashboard          from './pages/Dashboard.jsx';
import Tasks              from './pages/Tasks.jsx';
import TaskHistory        from './pages/TaskHistory.jsx';
import Analytics          from './pages/Analytics.jsx';
import Notifications      from './pages/Notifications.jsx';
import Settings           from './pages/Settings.jsx';

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login"    element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route element={<ProtectedRoute><Layout /></ProtectedRoute>}>
            <Route index              element={<Dashboard />} />
            <Route path="tasks"       element={<Tasks />} />
            <Route path="history"     element={<TaskHistory />} />
            <Route path="analytics"   element={<Analytics />} />
            <Route path="notifications" element={<Notifications />} />
            <Route path="settings"    element={<Settings />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
