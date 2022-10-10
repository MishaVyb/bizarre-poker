import React from "react";
import { Badge, Container, Stack } from "react-bootstrap";
import Navbar from "react-bootstrap/Navbar";
import { Link } from "react-router-dom";
import { useContext } from "react";
import { AuthContext } from "../../context";

const MyNavbar = () => {
  const { auth, setAuth } = useContext(AuthContext);

  let auth_link = <Link to={"login"}>login</Link>;
  if (auth) {
    auth_link = <Link to={"logout"}>logout</Link>;
  }

  return (
    <Navbar>
      <Container>
        <Navbar.Brand>
          <Link to={"/"}>bizarre poker</Link>
        </Navbar.Brand>
        <Navbar.Collapse className="justify-content-end">
          <Navbar.Text>
            <Link to={"/me"}>
              <Badge>{auth?.username}</Badge>
            </Link>
            {auth_link}
          </Navbar.Text>
        </Navbar.Collapse>
      </Container>
    </Navbar>
  );
};

export default MyNavbar;
