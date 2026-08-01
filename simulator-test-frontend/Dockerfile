FROM node:22-alpine AS build

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .

ARG VITE_API_BASE_URL=
ARG VITE_STUDY_ID=simulator-personal-fidelity-v1
ARG VITE_STUDY_TITLE=Simulator-Test
ARG VITE_SIMULATOR_PROVIDER=openai
ARG VITE_DEFAULT_LANGUAGE=zh-CN

ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
ENV VITE_STUDY_ID=${VITE_STUDY_ID}
ENV VITE_STUDY_TITLE=${VITE_STUDY_TITLE}
ENV VITE_SIMULATOR_PROVIDER=${VITE_SIMULATOR_PROVIDER}
ENV VITE_DEFAULT_LANGUAGE=${VITE_DEFAULT_LANGUAGE}

RUN npm run build

FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
