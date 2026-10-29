import "./landing.module.css";

/** Class names match the emitted stylesheet. This project's CSS pipeline does not return a CSS-module map. */
const styles: Record<string, string> = new Proxy(
  {},
  {
    get(_target, prop) {
      return typeof prop === "string" ? prop : undefined;
    },
  },
);

export default styles;
