import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { ProtectedRoute } from './components/ProtectedRoute';
import { DashboardLayout } from './layouts/DashboardLayout';

import { Login } from './pages/Login';
import { PublicStatus } from './pages/PublicStatus';
import { GuardDashboard } from './pages/GuardDashboard';
import { ManagerDashboard } from './pages/ManagerDashboard';
import { AdminSettings } from './pages/AdminSettings';

function App() {
  return (
    <AuthProvider>
      <Router>
        <Routes>
          {/* Rutas Públicas */}
          <Route path="/" element={<PublicStatus />} />
          <Route path="/login" element={<Login />} />

          {/* Rutas Protegidas - Dashboards */}
          <Route path="/dashboard" element={<DashboardLayout />}>
            
            {/* Guardia, Encargado y Admin pueden ver el panel de guardia */}
            <Route 
              path="guardia" 
              element={
                <ProtectedRoute allowedRoles={['guardia', 'encargado', 'admin']}>
                  <GuardDashboard />
                </ProtectedRoute>
              } 
            />

            {/* Solo Encargado y Admin pueden ver KPIs */}
            <Route 
              path="encargado" 
              element={
                <ProtectedRoute allowedRoles={['encargado', 'admin']}>
                  <ManagerDashboard />
                </ProtectedRoute>
              } 
            />

            {/* Solo Admin puede ver Settings */}
            <Route 
              path="admin" 
              element={
                <ProtectedRoute allowedRoles={['admin']}>
                  <AdminSettings />
                </ProtectedRoute>
              } 
            />
            
            {/* Redirección por defecto dentro del dashboard */}
            <Route path="" element={<Navigate to="/dashboard/guardia" replace />} />
          </Route>

          {/* Fallback */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Router>
    </AuthProvider>
  );
}

export default App;
