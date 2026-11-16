import React from "react";
import { Frame } from "../../App";
import { Entry } from "../entry";
import { navigate } from "../navigation";
export default function Screen() {
  return (
    <Frame>
      <Entry kind="receipt" go={navigate} />
    </Frame>
  );
}
