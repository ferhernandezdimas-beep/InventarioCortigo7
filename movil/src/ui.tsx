import React from "react";
import {
  ActivityIndicator,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
  type TextInputProps,
  type ViewStyle,
} from "react-native";
import Ionicons from "@expo/vector-icons/Ionicons";

export const C = {
  green: "#173D35",
  greenDark: "#102C26",
  sage: "#DCE7DD",
  pale: "#F0F4ED",
  cream: "#F6F5F0",
  white: "#FFFFFF",
  ink: "#232B27",
  muted: "#6F7971",
  border: "#E2E5DD",
  gold: "#CDBB95",
  clay: "#A55436",
  amber: "#946529",
  red: "#A43C3C",
};
export type IconName = React.ComponentProps<typeof Ionicons>["name"];
export function Icon({
  name,
  size = 22,
  color = C.green,
}: {
  name: IconName;
  size?: number;
  color?: string;
}) {
  return <Ionicons name={name} size={size} color={color} />;
}
export function Label({ children }: { children: React.ReactNode }) {
  return <Text style={s.label}>{children}</Text>;
}
export function Title({
  children,
  sub,
}: {
  children: React.ReactNode;
  sub?: string;
}) {
  return (
    <View style={{ gap: 8, marginBottom: 22 }}>
      <Text style={s.title}>{children}</Text>
      {sub && <Text style={s.muted}>{sub}</Text>}
    </View>
  );
}
export function Card({
  children,
  style,
}: {
  children: React.ReactNode;
  style?: ViewStyle;
}) {
  return <View style={[s.card, style]}>{children}</View>;
}
export function Button({
  title,
  onPress,
  icon,
  secondary,
  disabled,
  loading,
  danger,
}: {
  title: string;
  onPress: () => void;
  icon?: IconName;
  secondary?: boolean;
  disabled?: boolean;
  loading?: boolean;
  danger?: boolean;
}) {
  const color = secondary ? C.green : C.white;
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={title}
      disabled={disabled || loading}
      onPress={onPress}
      style={({ pressed }) => [
        s.button,
        secondary && s.secondary,
        danger && { backgroundColor: C.red },
        (disabled || loading) && { opacity: 0.5 },
        pressed && { opacity: 0.8 },
      ]}
    >
      {loading ? (
        <ActivityIndicator color={color} />
      ) : (
        <>
          {icon && <Icon name={icon} color={color} size={19} />}
          <Text style={{ color, fontWeight: "700", fontSize: 15 }}>
            {title}
          </Text>
        </>
      )}
    </Pressable>
  );
}
export function Field({ label, ...props }: TextInputProps & { label: string }) {
  return (
    <View style={{ gap: 8 }}>
      <Label>{label}</Label>
      <TextInput
        accessibilityLabel={label}
        placeholderTextColor="#9BA299"
        {...props}
        style={[
          s.input,
          props.multiline && { minHeight: 94, textAlignVertical: "top" },
          props.style,
        ]}
      />
    </View>
  );
}
export function Chip({
  label,
  active,
  onPress,
}: {
  label: string;
  active?: boolean;
  onPress?: () => void;
}) {
  return (
    <Pressable
      accessibilityRole={onPress ? "button" : "text"}
      onPress={onPress}
      style={[
        s.chip,
        active && { backgroundColor: C.green, borderColor: C.green },
      ]}
    >
      <Text
        style={{
          color: active ? C.white : C.green,
          fontSize: 12,
          fontWeight: "600",
        }}
      >
        {label}
      </Text>
    </Pressable>
  );
}
export function Note({
  children,
  warning = false,
}: {
  children: React.ReactNode;
  warning?: boolean;
}) {
  return (
    <View style={[s.note, warning && { backgroundColor: "#FAF0DF" }]}>
      <Icon
        name={warning ? "alert-circle-outline" : "information-circle-outline"}
        size={20}
        color={warning ? C.amber : C.green}
      />
      <Text
        style={{
          flex: 1,
          color: warning ? C.amber : C.green,
          lineHeight: 20,
          fontSize: 13,
        }}
      >
        {children}
      </Text>
    </View>
  );
}
export function Empty({
  title,
  description,
  icon = "leaf-outline",
}: {
  title: string;
  description: string;
  icon?: IconName;
}) {
  return (
    <Card style={{ alignItems: "center", paddingVertical: 36, gap: 12 }}>
      <Icon name={icon} size={34} color={C.muted} />
      <Text style={s.h2}>{title}</Text>
      <Text style={[s.muted, { textAlign: "center" }]}>{description}</Text>
    </Card>
  );
}
export const s = StyleSheet.create({
  screen: { flex: 1, backgroundColor: C.cream },
  content: {
    padding: 22,
    paddingBottom: 32,
    width: "100%",
    maxWidth: 760,
    alignSelf: "center",
    gap: 18,
  },
  title: {
    fontSize: 31,
    letterSpacing: -1,
    lineHeight: 36,
    color: C.ink,
    fontWeight: "700",
  },
  h2: { fontSize: 18, color: C.ink, fontWeight: "700", letterSpacing: -0.3 },
  body: { fontSize: 15, lineHeight: 23, color: C.ink },
  muted: { color: C.muted, lineHeight: 21, fontSize: 14 },
  tiny: { fontSize: 11, color: C.muted, lineHeight: 16 },
  eyebrow: {
    fontSize: 10,
    fontWeight: "800",
    letterSpacing: 2.4,
    color: C.clay,
  },
  label: { fontSize: 12, color: C.muted, fontWeight: "700" },
  row: { flexDirection: "row", alignItems: "center", gap: 12 },
  between: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 12,
  },
  card: {
    backgroundColor: C.white,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: C.border,
    padding: 20,
    gap: 14,
  },
  button: {
    backgroundColor: C.green,
    borderRadius: 13,
    minHeight: 52,
    paddingVertical: 14,
    paddingHorizontal: 20,
    flexDirection: "row",
    justifyContent: "center",
    alignItems: "center",
    gap: 10,
  },
  secondary: { backgroundColor: C.pale, borderWidth: 1, borderColor: C.border },
  input: {
    backgroundColor: C.white,
    minHeight: 52,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: "#CDD5CB",
    padding: 14,
    fontSize: 16,
    color: C.ink,
  },
  chip: {
    borderRadius: 20,
    borderWidth: 1,
    borderColor: C.border,
    paddingHorizontal: 14,
    paddingVertical: 10,
    backgroundColor: C.white,
  },
  note: {
    backgroundColor: C.pale,
    padding: 15,
    borderRadius: 13,
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 10,
  },
  line: { height: 1, backgroundColor: C.border },
  shadow: {
    shadowColor: C.greenDark,
    shadowOffset: { width: 0, height: 5 },
    shadowOpacity: 0.12,
    shadowRadius: 14,
    elevation: 3,
  },
});
