import React from "react";
import { Frame } from "../../App";
import { Assistant } from "../screens";
import { navigate } from "../navigation";
export default function Screen() {
  return (
    <Frame>
      <Assistant go={navigate} />
    </Frame>
  );
}
