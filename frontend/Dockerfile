# frontend/Dockerfile
FROM node:20-slim


WORKDIR /app

# Installation des dépendances
COPY package.json package-lock.json ./
RUN npm install

# Copie du code
COPY . .

EXPOSE 5173

# Lancement avec --host pour que Docker puisse y accéder
CMD ["npm", "run", "dev", "--", "--host"]