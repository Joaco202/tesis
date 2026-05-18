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
        .from('users') // Asumiendo tabla users para roles
        .select('role')
        .eq('id', userId)
        .single();
      
      if (data) setRole(data.role);
      else setRole('guardia'); // Fallback default
    } catch (error) {
      console.warn('Error fetching role, defaulting to guardia:', error);
      setRole('guardia'); // Fallback if table doesn't exist yet
    } finally {
      setLoading(false);
    }
  };

  const signIn = async (email, password) => {
    return supabase.auth.signInWithPassword({ email, password });
  };

  const signOut = async () => {
    return supabase.auth.signOut();
  };

  // Mock function for development without Supabase connection
  const mockSignIn = (roleType) => {
    setUser({ id: '123', email: 'test@ubb.cl' });
    setRole(roleType); // 'guardia', 'encargado', 'admin'
    setLoading(false);
  };

  return (
    <AuthContext.Provider value={{ user, role, loading, signIn, signOut, mockSignIn }}>
      {!loading && children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
