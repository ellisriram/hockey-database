import mysql from "mysql2";

const connection = mysql.createConnection({
  host: "localhost",
  user: "root",
  password: "njkl;'",
  database: "hockey_schema",
});

function connect() {
  connection.connect();
}

function query(sql, params, callback) {
  connection.query(sql, params, (error, results) => {
    if (error) throw error;
    callback(results);
  });
}

function disconnect() {
  connection.end();
}

export { connection, connect, query, disconnect };
