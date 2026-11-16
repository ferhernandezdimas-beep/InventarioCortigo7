import React from "react";
import { Frame } from "../../App";
import { POS } from "../screens";
import { navigate } from "../navigation";
export default function Screen() {
  return (
    <Frame>
      <POS go={navigate} />
    </Frame>
  );
}
