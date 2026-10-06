import { createContext, useCallback, useContext, useEffect, useState } from 'react';
import { api, json } from './api.js';

const AuthContext = createContext(null);
export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [ready, setReady] = useState(false);
  const [toast, setToast] = useState(null);
  useEffect(() => {
    if (localStorage.getItem('bharatlearn_token')) api('/auth/me').then(data => setUser(data.user)).catch(() => localStorage.removeItem('bharatlearn_token')).finally(() => setReady(true));
    else setReady(true);
  }, []);
  const signIn = useCallback(async (payload, path = '/auth/login') => {
    const data = await api(path, json('POST', payload));
    localStorage.setItem('bharatlearn_token', data.token);
    setUser(data.user);
    return data.user;
  }, []);
  const signOut = useCallback(() => { localStorage.removeItem('bharatlearn_token'); setUser(null); }, []);
  const notify = useCallback((message, type = 'success') => { setToast({ message, type }); window.setTimeout(() => setToast(null), 3400); }, []);
  return <AuthContext.Provider value={{ user, setUser, ready, signIn, signOut, toast, notify }}>{children}</AuthContext.Provider>;
}
export const useAuth = () => useContext(AuthContext);
