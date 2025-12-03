FROM node:20

WORKDIR /app

COPY package*.json ./
RUN npm install --legacy-peer-deps
RUN npm rebuild
RUN npm install @rollup/rollup-linux-x64-gnu --save-optional || true

COPY . ./

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]