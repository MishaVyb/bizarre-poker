import React, { useContext, useEffect } from "react";
import { Navigate } from "react-router-dom";
import { AuthContext } from "../context";
import AuthService from "../services/AuthService";

const Logout = () => {
  const { auth, setAuth } = useContext(AuthContext);

  // logout
  const logout = async () => {
    if (auth) {
        console.log("logout, remove this auth: ");
        console.log(auth);
        await AuthService.logout(auth.token);
        localStorage.removeItem("username");
        localStorage.removeItem("token");
        setAuth(null);
    } else {
        console.log('logging out when no auth provided')
    }
  }

  // trigger on component mount
  useEffect(() => {
    logout()
  });

  return (
    <div>
      <h3>see ya</h3>
      <Navigate to="/login" replace />;
    </div>
  );
};

export default Logout;
