module.exports = {
  apps: [
    {
      name: "liga",
      cwd: "/var/www/liga",
      script: "/var/www/liga/.venv/bin/gunicorn",
      args: "-w 1 --threads 4 -b 127.0.0.1:8000 --timeout 60 run:app",
      interpreter: "none",
    },
  ],
};
