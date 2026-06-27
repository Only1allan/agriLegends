"use client";

import { createContext, useContext, useState, useEffect, ReactNode } from "react";

interface AuthState {
  isAuthenticated: boolean;
  farmerId: string | null;
  name: string | null;
  token: string | null;
  login: (token: string, farmerId: string, name: string) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthState>({
  isAuthenticated: false,
  farmerId: null,
  name: null,
  token: null,
  login: () => {},
  logout: () => {},
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [farmerId, setFarmerId] = useState<string | null>(null);
  const [name, setName] = useState<string | null>(null);
  const [token, setTokenState] = useState<string | null>(null);

  useEffect(() => {
    if (typeof window !== "undefined") {
      setFarmerId(localStorage.getItem("farmwise_farmer_id"));
      setName(localStorage.getItem("farmwise_name"));
      setTokenState(localStorage.getItem("farmwise_token"));
    }
  }, []);

  const login = (t: string, fid: string, n: string) => {
    localStorage.setItem("farmwise_token", t);
    localStorage.setItem("farmwise_farmer_id", fid);
    localStorage.setItem("farmwise_name", n);
    setTokenState(t);
    setFarmerId(fid);
    setName(n);
  };

  const logout = () => {
    localStorage.removeItem("farmwise_token");
    localStorage.removeItem("farmwise_farmer_id");
    localStorage.removeItem("farmwise_name");
    setTokenState(null);
    setFarmerId(null);
    setName(null);
  };

  return (
    <AuthContext.Provider
      value={{
        isAuthenticated: !!token,
        farmerId,
        name,
        token,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
