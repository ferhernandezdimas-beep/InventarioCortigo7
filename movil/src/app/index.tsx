import React from "react";
import { Frame } from "../../App";
import { Home } from "../screens";
import { navigate } from "../navigation";
export default function Screen() {
  return (
    <Frame>
      <Home go={navigate} />
    </Frame>
  );
}
