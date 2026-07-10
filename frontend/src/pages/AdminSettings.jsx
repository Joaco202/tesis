import React, { useState, useEffect } from 'react';
import { UserPlus, Shield, Trash2, Edit, X, Check, Search, Lock } from 'lucide-react';
import { supabase } from '../lib/supabase';
import { createClient } from '@supabase/supabase-js';

const modalOverlayStyle = {
  position: 'fixed',
  top: 0,
  left: 0,
  right: 0,
  bottom: 0,
  backgroundColor: 'rgba(15, 23, 42, 0.6)',
  backdropFilter: 'blur(8px)',
  display: 'flex',
  justifyContent: 'center',
  alignItems: 'center',
  zIndex: 1000,
};

const modalContentStyle = {
  width: '100%',
  maxWidth: '500px',
  backgroundColor: 'var(--bg-secondary)',
  borderRadius: 'var(--radius-lg)',
  border: '1px solid var(--border-color)',
  boxShadow: 'var(--shadow-lg)',
  padding: '2rem',
  position: 'relative',
};

const FloatingInput = ({ label, type = 'text', value, onChange, placeholder, required = false, minLength }) => {
  const [isFocused, setIsFocused] = useState(false);
  const [isHovered, setIsHovered] = useState(false);

  const isFloated = isFocused || (value && value.length > 0);

  return (
    <div 
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      style={{ position: 'relative', marginTop: '1.25rem', width: '100%' }}
    >
      <input 
        type={type} 
        value={value} 
        onChange={onChange}
        placeholder={isFocused ? placeholder : ''}
        required={required}
        minLength={minLength}
        onFocus={() => setIsFocused(true)}
        onBlur={() => setIsFocused(false)}
        className="input-field"
        style={{
          height: '42px',
          padding: '0 1rem',
          border: (isFocused || isHovered) ? '1px solid #ffffff' : '1px solid var(--border-color)',
          borderRadius: 'var(--radius-md)',
          backgroundColor: 'var(--bg-secondary)',
          color: 'var(--text-primary)',
          fontSize: '0.875rem',
          transition: 'all 0.2s ease',
          outline: 'none',
          width: '100%',
        }}
      />
      <span 
        style={{ 
          position: 'absolute', 
          top: isFloated ? '-9px' : '50%',
          left: '12px', 
          transform: isFloated ? 'none' : 'translateY(-50%)',
          backgroundColor: 'var(--bg-secondary)', 
          padding: '0 6px', 
          fontSize: isFloated ? '0.75rem' : '0.875rem', 
          fontWeight: 500,
          color: (isFocused || isHovered) ? 'var(--text-primary)' : 'var(--text-secondary)',
          pointerEvents: 'none',
          transition: 'all 0.2s ease',
        }}
      >
        {label}
      </span>
    </div>
  );
};

const FloatingSelect = ({ label, value, onChange, options, required = false }) => {
  const [isFocused, setIsFocused] = useState(false);
  const [isHovered, setIsHovered] = useState(false);

  return (
    <div 
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      style={{ position: 'relative', marginTop: '1.25rem', width: '100%' }}
    >
      <select 
        value={value} 
        onChange={onChange}
        required={required}
        onFocus={() => setIsFocused(true)}
        onBlur={() => setIsFocused(false)}
        className="input-field"
        style={{
          height: '42px',
          padding: '0 1rem',
          border: (isFocused || isHovered) ? '1px solid #ffffff' : '1px solid var(--border-color)',
          borderRadius: 'var(--radius-md)',
          backgroundColor: 'var(--bg-secondary)',
          color: 'var(--text-primary)',
          fontSize: '0.875rem',
          transition: 'all 0.2s ease',
          outline: 'none',
          width: '100%',
          cursor: 'pointer',
        }}
      >
        {options.map(opt => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
      <span 
        style={{ 
          position: 'absolute', 
          top: '-9px', 
          left: '12px', 
          backgroundColor: 'var(--bg-secondary)', 
          padding: '0 6px', 
          fontSize: '0.75rem', 
          fontWeight: 500,
          color: (isFocused || isHovered) ? 'var(--text-primary)' : 'var(--text-secondary)',
          pointerEvents: 'none',
          transition: 'all 0.2s ease',
        }}
      >
        {label}
      </span>
    </div>
  );
};

export const AdminSettings = () => {
  const [users, setUsers] = useState([]);
  const [roles, setRoles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  
  // Modal states
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [editingUser, setEditingUser] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [form, setForm] = useState({
    nombre: '',
    email: '',
    password: '',
    rol: 'guardia' // default role
  });
  const [editForm, setEditForm] = useState({
    nombre: '',
    rol: 'guardia'
  });

  const fetchUsersAndRoles = async () => {
    try {
      setLoading(true);
      // Fetch users with role details
      const { data: usersData, error: usersError } = await supabase
        .from('usuarios')
        .select('id, nombre, email, estado, rol_id, roles ( id, nombre )')
        .eq('eliminado', false)
        .order('created_at', { ascending: false });

      if (usersError) throw usersError;
      setUsers(usersData || []);

      // Fetch roles
      const { data: rolesData, error: rolesError } = await supabase
        .from('roles')
        .select('*')
        .order('id', { ascending: true });

      if (rolesError) throw rolesError;
      setRoles((rolesData || []).filter(r => r.nombre !== 'visitante'));
    } catch (err) {
      console.error('Error fetching users and roles:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsersAndRoles();
  }, []);

  const handleToggleStatus = async (user) => {
    try {
      const newStatus = !user.estado;
      const { error } = await supabase
        .from('usuarios')
        .update({ estado: newStatus })
        .eq('id', user.id);

      if (error) throw error;
      
      // Update local state
      setUsers(prev => prev.map(u => u.id === user.id ? { ...u, estado: newStatus } : u));
    } catch (err) {
      console.error('Error toggling user status:', err);
      alert('Error al cambiar el estado del usuario: ' + err.message);
    }
  };

  const handleDeleteUser = async (userId) => {
    if (!window.confirm('¿Estás seguro de que deseas eliminar este usuario de la aplicación?')) {
      return;
    }
    try {
      const { error } = await supabase
        .from('usuarios')
        .update({ eliminado: true })
        .eq('id', userId);

      if (error) throw error;

      // Update local state
      setUsers(prev => prev.filter(u => u.id !== userId));
      alert('Usuario eliminado de la aplicación con éxito.');
    } catch (err) {
      console.error('Error deleting user:', err);
      alert('Error al eliminar el usuario: ' + err.message);
    }
  };

  const handleOpenEditModal = (user) => {
    setEditingUser(user);
    setEditForm({
      nombre: user.nombre,
      rol: user.roles?.nombre || 'guardia'
    });
    setIsEditModalOpen(true);
  };

  const handleEditUser = async (e) => {
    e.preventDefault();
    if (!editForm.nombre.trim()) {
      alert('Por favor, completa el nombre.');
      return;
    }
    setSubmitting(true);
    try {
      const selectedRole = roles.find(r => r.nombre === editForm.rol);
      if (!selectedRole) {
        throw new Error('Rol seleccionado no válido.');
      }

      const { error } = await supabase
        .from('usuarios')
        .update({
          nombre: editForm.nombre.trim(),
          rol_id: selectedRole.id
        })
        .eq('id', editingUser.id);

      if (error) throw error;

      alert('Usuario actualizado con éxito.');
      setIsEditModalOpen(false);
      setEditingUser(null);
      fetchUsersAndRoles();
    } catch (err) {
      console.error('Error updating user:', err);
      alert('Error al actualizar el usuario: ' + err.message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleCreateUser = async (e) => {
    e.preventDefault();
    if (!form.nombre.trim() || !form.email.trim() || !form.password.trim()) {
      alert('Por favor, completa todos los campos.');
      return;
    }

    setSubmitting(true);
    try {
      const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
      const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;

      if (!supabaseUrl || !supabaseAnonKey) {
        throw new Error('No se encontraron las variables de configuración de Supabase.');
      }

      // Crear un cliente temporal con persistSession: false
      // Esto previene que se reemplace la sesión del administrador activo
      const tempClient = createClient(supabaseUrl, supabaseAnonKey, {
        auth: {
          persistSession: false
        }
      });

      // Registrar el usuario en Supabase Auth pasándole los metadatos de nombre y rol
      const { data, error: authError } = await tempClient.auth.signUp({
        email: form.email.trim(),
        password: form.password.trim(),
        options: {
          data: {
            nombre: form.nombre.trim(),
            rol: form.rol
          }
        }
      });

      if (authError) throw authError;

      alert('Usuario registrado con éxito.');
      
      setIsModalOpen(false);
      setForm({ nombre: '', email: '', password: '', rol: 'guardia' });
      
      // Volver a cargar la lista de usuarios
      fetchUsersAndRoles();
    } catch (err) {
      console.error('Error creating user:', err);
      alert('Error al crear el usuario: ' + err.message);
    } finally {
      setSubmitting(false);
    }
  };

  const filteredUsers = users.filter(user => 
    user.nombre.toLowerCase().includes(search.toLowerCase()) ||
    user.email.toLowerCase().includes(search.toLowerCase()) ||
    (user.roles && user.roles.nombre.toLowerCase().includes(search.toLowerCase()))
  );

  return (
    <>
      <div className="animate-fade-in">
        <div className="flex-between" style={{ marginBottom: '2rem' }}>
          <div>
            <h1 style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--text-primary)' }}>Administración del Sistema</h1>
            <p style={{ color: 'var(--text-secondary)' }}>Gestión de Usuarios y Roles</p>
          </div>
          <button className="btn btn-primary" onClick={() => setIsModalOpen(true)}>
            <UserPlus size={18} /> Nuevo Usuario
          </button>
        </div>

        <div className="card" style={{ marginBottom: '2rem' }}>
          <div className="flex-between" style={{ marginBottom: '1.5rem', flexWrap: 'wrap', gap: '1rem' }}>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Shield size={20} color="var(--ubb-blue)" /> Control de Acceso
            </h2>
            <div style={{ position: 'relative' }}>
              <Search size={18} style={{ position: 'absolute', left: '0.75rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-secondary)' }} />
              <input 
                type="text" 
                placeholder="Buscar usuario..." 
                className="input-field" 
                style={{ paddingLeft: '2.5rem', width: '250px', height: '38px' }}
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
          </div>

          {loading ? (
            <div className="flex-center animate-pulse" style={{ height: '200px' }}>
              <p style={{ color: 'var(--text-secondary)' }}>Cargando lista de usuarios...</p>
            </div>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
                <thead>
                  <tr style={{ borderBottom: '2px solid var(--border-color)', color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
                    <th style={{ padding: '1rem 0.5rem' }}>Nombre</th>
                    <th style={{ padding: '1rem 0.5rem' }}>Correo</th>
                    <th style={{ padding: '1rem 0.5rem', textAlign: 'center' }}>Rol</th>
                    <th style={{ padding: '1rem 0.5rem', textAlign: 'center' }}>Estado</th>
                    <th style={{ padding: '1rem 0.5rem', textAlign: 'right' }}>Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredUsers.map((u) => (
                    <tr key={u.id} style={{ borderBottom: '1px solid var(--border-color)' }}>
                      <td style={{ padding: '1rem 0.5rem', fontWeight: 500 }}>{u.nombre}</td>
                      <td style={{ padding: '1rem 0.5rem', color: 'var(--text-secondary)' }}>{u.email}</td>
                      <td style={{ padding: '1rem 0.5rem', textAlign: 'center' }}>
                        <span className="badge badge-primary" style={{ textTransform: 'capitalize' }}>
                          {u.roles?.nombre || 'Sin Rol'}
                        </span>
                      </td>
                      <td style={{ padding: '1rem 0.5rem', textAlign: 'center' }}>
                        <button 
                          onClick={() => handleToggleStatus(u)}
                          className={`badge ${u.estado ? 'badge-success' : 'badge-danger'}`}
                          style={{ border: 'none', cursor: 'pointer', fontFamily: 'inherit' }}
                          title="Haga clic para cambiar el estado"
                        >
                          {u.estado ? 'Activo' : 'Inactivo'}
                        </button>
                      </td>
                      <td style={{ padding: '1rem 0.5rem', textAlign: 'right' }}>
                        <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
                          <button 
                            className="btn btn-secondary" 
                            style={{ padding: '0.25rem', color: 'var(--text-secondary)' }} 
                            title="Editar usuario"
                            onClick={() => handleOpenEditModal(u)}
                          >
                            <Edit size={16} />
                          </button>
                          <button 
                            className="btn btn-secondary" 
                            style={{ padding: '0.25rem', color: 'var(--status-danger)' }} 
                            title="Eliminar de la aplicación"
                            onClick={() => handleDeleteUser(u.id)}
                          >
                            <Trash2 size={16} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                  {filteredUsers.length === 0 && (
                    <tr>
                      <td colSpan="5" style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
                        No se encontraron usuarios.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* Modal para Crear Usuario */}
      {isModalOpen && (
        <div style={modalOverlayStyle}>
          <div style={modalContentStyle} className="animate-fade-in">
            <div className="flex-between" style={{ marginBottom: '1.5rem', borderBottom: '1px solid var(--border-color)', paddingBottom: '1rem' }}>
              <h3 style={{ fontSize: '1.25rem', fontWeight: 600 }}>Crear usuario</h3>
              <button onClick={() => setIsModalOpen(false)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-secondary)' }}>
                <X size={20} />
              </button>
            </div>
            
            <form onSubmit={handleCreateUser} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <FloatingInput 
                label="Nombre Completo *"
                placeholder="Ej. Juan Pérez"
                value={form.nombre}
                onChange={(e) => setForm(prev => ({ ...prev, nombre: e.target.value }))}
                required
              />

              <FloatingInput 
                label="Correo *"
                type="email"
                placeholder="Ej. jperez@ubiobio.cl"
                value={form.email}
                onChange={(e) => setForm(prev => ({ ...prev, email: e.target.value }))}
                required
              />

              <FloatingInput 
                label="Contraseña *"
                type="password"
                placeholder="Mínimo 6 caracteres"
                value={form.password}
                onChange={(e) => setForm(prev => ({ ...prev, password: e.target.value }))}
                required
                minLength={6}
              />

              <FloatingSelect 
                label="Rol del Usuario *"
                value={form.rol}
                onChange={(e) => setForm(prev => ({ ...prev, rol: e.target.value }))}
                options={roles.map(r => ({
                  value: r.nombre,
                  label: r.nombre.charAt(0).toUpperCase() + r.nombre.slice(1)
                }))}
                required
              />
              
              <div style={{ display: 'flex', gap: '1rem', justifyContent: 'flex-end', marginTop: '1.5rem' }}>
                <button type="button" className="btn btn-secondary" onClick={() => setIsModalOpen(false)}>Cancelar</button>
                <button type="submit" className="btn btn-primary" disabled={submitting}>
                  {submitting ? 'Creando...' : 'Crear Usuario'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal para Editar Usuario */}
      {isEditModalOpen && (
        <div style={modalOverlayStyle}>
          <div style={modalContentStyle} className="animate-fade-in">
            <div className="flex-between" style={{ marginBottom: '1.5rem', borderBottom: '1px solid var(--border-color)', paddingBottom: '1rem' }}>
              <h3 style={{ fontSize: '1.25rem', fontWeight: 600 }}>Editar usuario</h3>
              <button onClick={() => { setIsEditModalOpen(false); setEditingUser(null); }} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-secondary)' }}>
                <X size={20} />
              </button>
            </div>
            
            <form onSubmit={handleEditUser} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <FloatingInput 
                label="Nombre Completo *"
                placeholder="Ej. Juan Pérez"
                value={editForm.nombre}
                onChange={(e) => setEditForm(prev => ({ ...prev, nombre: e.target.value }))}
                required
              />

              <FloatingSelect 
                label="Rol del Usuario *"
                value={editForm.rol}
                onChange={(e) => setEditForm(prev => ({ ...prev, rol: e.target.value }))}
                options={roles.map(r => ({
                  value: r.nombre,
                  label: r.nombre.charAt(0).toUpperCase() + r.nombre.slice(1)
                }))}
                required
              />
              
              <div style={{ display: 'flex', gap: '1rem', justifyContent: 'flex-end', marginTop: '1.5rem' }}>
                <button type="button" className="btn btn-secondary" onClick={() => { setIsEditModalOpen(false); setEditingUser(null); }}>Cancelar</button>
                <button type="submit" className="btn btn-primary" disabled={submitting}>
                  {submitting ? 'Guardando...' : 'Guardar Cambios'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
};
