import "./../node_modules/bootswatch/dist/sketchy/bootstrap.css";

import { AuthContext } from "./context";
import { useEffect, useState } from "react";
import  { getRouter, getRouter_fake } from "./routes/Router";
import { RouterProvider } from "react-router-dom";
import AuthService from "./services/AuthService";
import GameService from "./services/GameService";

function App() {
  const [auth, setAuth] = useState(null);

  const noTokenRouter = getRouter(new AuthService(), new GameService())
  const [router, setRouter] = useState(noTokenRouter);

  useEffect(() => {
    if (localStorage.getItem("token")) {
      const auth = {
        username: localStorage.getItem("username"),
        token: localStorage["token"],
      };
      setAuth(auth);
    }

    const authService = new AuthService(auth?.token)
    // const gameService = new GameService()
    const tokenRouter = getRouter(authService, GameService)
    setRouter(tokenRouter)

  }, [auth?.token]);

  console.log("APP RUNNING WITH AUTH: ", {...auth});


  return (
    <div className="App">
      <AuthContext.Provider value={{ auth, setAuth }}>
        <RouterProvider router={router} />
      </AuthContext.Provider>
    </div>
  );
}

export default App;
