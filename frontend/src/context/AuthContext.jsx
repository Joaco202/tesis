import React, { createContext, useContext, useEffect, useState } from 'react';
import { supabase } from '../lib/supabase';

const AuthContext = createContext({});

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [role, setRole] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Verificar sesión actual
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (session) {
        setUser(session.user);
        fetchUserRole(session.user.id);
      } else {
        setLoading(false);
      }
    });

    // Escuchar cambios de autenticación
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      if (session) {
        setLoading(true); // Bloquear render hasta que el rol esté listo
        setUser(session.user);
        fetchUserRole(session.user.id);
      } else {
        setUser(null);
        setRole(null);
        setLoading(false);
      }
    });

    return () => subscription.unsubscribe();
  }, []);

  const fetchUserRole = async (userId) => {
    try {
      const { data, error } = await supabase
        .from('usuarios')
        .select('rol_id, estado, eliminado, roles ( nombre )')
        .eq('id', userId)
        .single();
      
      if (error) {
        console.warn('Error al obtener rol/estado del usuario:', error);
      }
      
      if (data) {
        if (data.estado === false || data.eliminado === true) {
          console.warn('Usuario inactivo o eliminado, cerrando sesión');
          await supabase.auth.signOut();
          setUser(null);
          setRole(null);
          return;
        }

        if (data.roles && data.roles.nombre) {
          const dbRole = data.roles.nombre;
          const mappedRole = dbRole === 'administrador' ? 'admin' : dbRole;
          setRole(mappedRole);
        } else {
          setRole('guardia'); 
        }
      } else {
        setRole('guardia');
      }
    } catch (error) {
      console.warn('Error fetching role, defaulting to guardia:', error);
      setRole('guardia'); 
    } finally {
      setLoading(false);
    }
  };

  const signIn = async (email, password) => {
    const { data, error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) return { error };

    if (data && data.user) {
      const { data: userData, error: userError } = await supabase
        .from('usuarios')
        .select('estado, eliminado')
        .eq('id', data.user.id)
        .single();

      if (userError) {
        console.error('Error al obtener estado del usuario en login:', userError);
      }

      if (userData && (userData.estado === false || userData.eliminado === true)) {
        await supabase.auth.signOut();
        return { error: new Error('Usuario inactivo o eliminado') };
      }
    }
    return { data, error: null };
  };

  const signOut = async () => {
    return supabase.auth.signOut();
  };

  return (
    <AuthContext.Provider value={{ user, role, loading, signIn, signOut }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
