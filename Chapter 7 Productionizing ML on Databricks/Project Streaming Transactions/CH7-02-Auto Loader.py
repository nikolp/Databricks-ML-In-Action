# Databricks notebook source
# MAGIC %md
# MAGIC Chapter 7: Productionizing ML on Databricks
# MAGIC
# MAGIC ## Transaction data - Streaming as Delta into a table using Auto Loader
# MAGIC
# MAGIC We have created a feature for our model based on the Product column so we no longer create the nulls.

# COMMAND ----------

# MAGIC %md ##Run Setup

# COMMAND ----------

# MAGIC %run ../../global-setup $project_name=synthetic_transactions $env=prod

# COMMAND ----------

# DBTITLE 1,Variables
dbutils.widgets.text('raw_table_name','prod_transactions','Enter table name for the raw delta')
table_name = dbutils.widgets.get('raw_table_name')
raw_data_location = f"{volume_file_path}/{table_name}/data/" 
schema_location = f"{volume_file_path}/{table_name}/schema"
checkpoint_location = f"{volume_file_path}/{table_name}/checkpoint"

# COMMAND ----------

# DBTITLE 1,Use to reset for fresh table, schema, checkpoints
if not spark.catalog.tableExists(table_name) or spark.table(tableName=table_name).isEmpty():
  sql(f"""CREATE TABLE IF NOT EXISTS {table_name} (CustomerID INT, Amount FLOAT, TransactionTimestamp TIMESTAMP, Product STRING) TBLPROPERTIES (delta.enableChangeDataFeed = true)""")

# COMMAND ----------

# DBTITLE 1,Optimization settings and reduce the number of files that must be read to determine schema
spark.conf.set("spark.databricks.delta.optimizeWrite.enabled", True)
spark.conf.set("spark.databricks.delta.autoCompact.enabled", True)
spark.conf.set("spark.databricks.cloudFiles.schemaInference.sampleSize.numFiles",1)
spark.conf.set("spark.databricks.delta.schema.autoMerge.enabled", True)

# COMMAND ----------

import time

#giving the generator time to start 15 seconds
time.sleep(15)

# COMMAND ----------

# DBTITLE 1,Readstream
stream = spark.readStream \
  .format("cloudFiles") \
  .option("cloudFiles.format", "json") \
  .option("cloudFiles.schemaHints","CustomerID int, Amount float, TransactionTimestamp timestamp, Product string") \
  .option("cloudFiles.inferColumnTypes","true") \
  .option("cloudFiles.schemaEvolutionMode", "addNewColumns") \
  .option("cloudFiles.schemaLocation", schema_location) \
  .load(raw_data_location) \
  .select("*") \
  .writeStream \
  .format("delta") \
  .outputMode("append") \
  .option("checkpointLocation", checkpoint_location) \
  .option("mergeSchema", "true") \
  .trigger(processingTime="10 seconds") \
  .toTable(tableName=table_name)
