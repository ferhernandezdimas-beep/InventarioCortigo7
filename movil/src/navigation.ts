import { router } from "expo-router";
import type { Route } from "./screens";
export function navigate(route: Route) {
  router.navigate(route === "home" ? "/" : `/${route}`);
}
