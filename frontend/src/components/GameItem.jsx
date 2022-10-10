import React from "react";
import { Badge, Button, Card, Col, Row } from "react-bootstrap";

const GameItem = ({ game }) => {
  const playerItems = game.players.map((player) => (
    <Badge bg="light" text="dark" key={player}>
      <h6>{player}</h6>
    </Badge>
  ));
  return (
    <Card>
      <Row>
        <Col>
          <h3>{game.id}</h3>
        </Col>
        <Col md="auto">{playerItems}</Col>
        <Col md="auto">
          <Button variant="outline-primary" size="sm">
            join
          </Button>
        </Col>
      </Row>
    </Card>
  );
};

export default GameItem;
