import React from "react";
import { Stack } from "expo-router";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { AppProvider } from "../context";
import { ErrorBoundary } from "../../App";
export default function RootLayout() {
  return (
    <SafeAreaProvider>
      <ErrorBoundary>
        <AppProvider>
          <Stack screenOptions={{ headerShown: false, animation: "fade" }} />
        </AppProvider>
      </ErrorBoundary>
    </SafeAreaProvider>
  );
}
