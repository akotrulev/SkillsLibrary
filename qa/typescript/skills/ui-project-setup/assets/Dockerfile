FROM mcr.microsoft.com/playwright:v1.64.0-noble
WORKDIR /work
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
ENV CI=true
ENTRYPOINT ["npx", "playwright", "test"]
