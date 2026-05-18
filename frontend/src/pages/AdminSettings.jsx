import React, { useState } from 'react';
import { UserPlus, Shield, Trash2, Edit } from 'lucide-react';

const mockUsers = [
  { id: '1', name: 'Ronald Lagos', email: 'rlagos@ubiobio.cl', role: 'encargado', status: 'Activo' },
  { id: '2', name: 'Guardia Turno A', email: 'guardia_a@ubiobio.cl', role: 'guardia', status: 'Activo' },
  { id: '3', name: 'Admin TI', email: 'admin@ubiobio.cl', role: 'admin', status: 'Activo' },
  { id: '4', name: 'Guardia Turno B', email: 'guardia_b@ubiobio.cl', role: 'guardia', status: 'Inactivo' },
];

export const AdminSettings = () => {
  const [users, setUsers] = useState(mockUsers);

  return (
    <div className="animate-fade-in">
      <div className="flex-between" style={{ marginBottom: '2rem' }}>
        <div>
          <h1 style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--text-primary)' }}>Administración del Sistema</h1>
          <p style={{ color: 'var(--text-secondary)' }}>Gestión de Usuarios y Roles (TI)</p>
        </div>
        <button className="btn btn-primary">
          <UserPlus size={18} /> Nuevo Usuario
        </button>
      </div>

      <div className="card">
        <h2 style={{ fontSize: '1.25rem', fontWeight: 600, marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Shield size={20} color="var(--ubb-blue)" /> Control de Acceso
        </h2>

        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
            <thead>
              <tr style={{ borderBottom: '2px solid var(--border-color)', color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
                <th style={{ padding: '1rem 0.5rem' }}>Nombre</th>
                <th style={{ padding: '1rem 0.5rem' }}>Correo Institucional</th>
                <th style={{ padding: '1rem 0.5rem' }}>Rol</th>
                <th style={{ padding: '1rem 0.5rem' }}>Estado</th>
                <th style={{ padding: '1rem 0.5rem', textAlign: 'right' }}>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {users.map((user) => (
                <tr key={user.id} style={{ borderBottom: '1px solid var(--border-color)' }}>
                  <td style={{ padding: '1rem 0.5rem', fontWeight: 500 }}>{user.name}</td>
                  <td style={{ padding: '1rem 0.5rem', color: 'var(--text-secondary)' }}>{user.email}</td>
                  <td style={{ padding: '1rem 0.5rem' }}>
                    <span className="badge badge-primary" style={{ textTransform: 'capitalize' }}>{user.role}</span>
                  </td>
                  <td style={{ padding: '1rem 0.5rem' }}>
                    <span className={`badge ${user.status === 'Activo' ? 'badge-success' : 'badge-danger'}`}>
                      {user.status}
                    </span>
                  </td>
                  <td style={{ padding: '1rem 0.5rem', textAlign: 'right' }}>
                    <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
                      <button className="btn btn-secondary" style={{ padding: '0.25rem' }} title="Editar">
                        <Edit size={16} />
                      </button>
                      <button className="btn btn-secondary" style={{ padding: '0.25rem', color: 'var(--status-danger)' }} title="Desactivar">
                        <Trash2 size={16} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
