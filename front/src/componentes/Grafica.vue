<script setup>
import { BarChart, LineChart, ScatterChart } from "echarts/charts";
import { GridComponent, LegendComponent, MarkAreaComponent, MarkLineComponent, TooltipComponent } from "echarts/components";
import * as echarts from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { onBeforeUnmount, onMounted, ref, watch } from "vue";

echarts.use([BarChart, LineChart, ScatterChart, GridComponent, LegendComponent, MarkAreaComponent,
  MarkLineComponent, TooltipComponent, CanvasRenderer]);

const props = defineProps({
  titulo: { type: String, required: true },
  explicacion: { type: String, default: "" },
  opcion: { type: Object, required: true },
  alto: { type: Number, default: 300 },
});

const contenedor = ref(null);
let grafica = null;
let observadorTamano = null;

onMounted(() => {
  grafica = echarts.init(contenedor.value);
  grafica.setOption(props.opcion);
  observadorTamano = new ResizeObserver(() => grafica.resize());
  observadorTamano.observe(contenedor.value);
});

watch(() => props.opcion, (opcionNueva) => grafica?.setOption(opcionNueva, { notMerge: true }));

onBeforeUnmount(() => {
  observadorTamano?.disconnect();
  grafica?.dispose();
});
</script>

<template>
  <figure class="grafica">
    <h4>{{ titulo }}</h4>
    <p v-if="explicacion">{{ explicacion }}</p>
    <div ref="contenedor" :style="{ height: `${alto}px` }" role="img" :aria-label="titulo"></div>
  </figure>
</template>

<style scoped>
figure { margin: 0; min-width: 0; }
</style>
