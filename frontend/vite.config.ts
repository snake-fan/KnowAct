import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const apiProxyTarget = process.env.VITE_API_PROXY_TARGET || "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          return manualChunkName(id);
        }
      }
    }
  },
  server: {
    proxy: {
      "/api": apiProxyTarget,
      "/health": apiProxyTarget
    }
  }
});

function manualChunkName(id: string): string | undefined {
  const normalizedId = id.replaceAll("\\", "/");
  const nodeModulesMarker = "/node_modules/";
  const nodeModulesIndex = normalizedId.lastIndexOf(nodeModulesMarker);
  if (nodeModulesIndex < 0) {
    return undefined;
  }

  const packagePath = normalizedId.slice(nodeModulesIndex + nodeModulesMarker.length);
  if (packagePath.startsWith("react/") || packagePath.startsWith("react-dom/")) {
    return "vendor-react";
  }

  if (packagePath.startsWith("@antv/g6/")) {
    return "vendor-antv-g6";
  }
  if (
    packagePath.startsWith("@antv/layout/")
    || packagePath.startsWith("dagre/")
    || packagePath.startsWith("graphlib/")
    || packagePath.startsWith("lodash/")
    || packagePath.startsWith("ml-")
  ) {
    return "vendor-antv-layout";
  }
  if (packagePath.startsWith("@antv/component/")) {
    return "vendor-antv-component";
  }
  if (
    packagePath.startsWith("@antv/g/")
    || packagePath.startsWith("@antv/g-canvas/")
    || packagePath.startsWith("@antv/g-lite/")
    || packagePath.startsWith("@antv/g-math/")
    || packagePath.startsWith("@antv/g-plugin-dragndrop/")
    || packagePath.startsWith("@antv/vendor/")
  ) {
    return "vendor-antv-renderer";
  }
  if (
    packagePath.startsWith("@antv/algorithm/")
    || packagePath.startsWith("@antv/event-emitter/")
    || packagePath.startsWith("@antv/expr/")
    || packagePath.startsWith("@antv/graphlib/")
    || packagePath.startsWith("@antv/hierarchy/")
    || packagePath.startsWith("@antv/scale/")
    || packagePath.startsWith("@antv/util/")
  ) {
    const packageName = packagePath.split("/")[1] ?? "misc";
    return `vendor-antv-${packageName}`;
  }
  if (packagePath.startsWith("d3-")) {
    return "vendor-d3";
  }
  if (packagePath.startsWith("html2canvas/")) {
    return "vendor-html2canvas";
  }

  return undefined;
}
