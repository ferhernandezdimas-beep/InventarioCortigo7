import React from "react";
import { Frame } from "../../App";
import { Inventory } from "../screens";
import { navigate } from "../navigation";
export default function Screen() {
  return (
    <Frame>
      <Inventory go={navigate} />
    </Frame>
  );
}
