(ns framework.utils
  (:require
   [clojure.edn :as edn]
   [clojure.pprint :refer [pprint]]
   [clojure.string :as s]
   [promesa.core :as p]
   ["fs" :as fs]
   ["fs/promises" :as fsp]
   ["path" :as path]))

(defn pprint-str
  [data]
  (with-out-str
    (pprint data)))

(defn read-file
  [filename]
  (.readFileSync fs filename #js {:encoding "utf-8"}))

(defn read-edn-file
  [filename]
  (-> filename
      (read-file)
      (edn/read-string)))

(defn write-edn-file
  [filename contents]
  (.writeFileSync fs filename (pprint-str contents) #js {:encoding "utf-8"}))

(defn file-exists?
  [filepath]
  (-> (.stat fsp filepath)
      (p/then (fn [stats] (.isFile stats)))
      (p/catch (constantly false))))

(defn url->filepath
  [root url]
  (let [dirpath (subs url 1)
        dirpath (.replace dirpath "/" (.-sep path))]
    (.resolve path (.join path root dirpath))))

(defn slugify
  [text]
  (let [charlist (set "abcdefghijklmnopqrstuvwxyz0123456789")]
    (loop [slug ""
           remaining (s/lower-case text)]
      (let [[char & remaining] remaining
            last-char (last slug)]
        (cond
          (nil? char)
          slug

          (charlist char)
          (recur (str slug char) remaining)

          (and last-char
               (not= last-char "-")
               remaining
               (charlist (first remaining)))
          (recur (str slug "-") remaining)

          :else
          (recur slug remaining))))))

(defn uid->base64
  [uidstr]
  (let [buf (js/Buffer.from (s/reverse uidstr))]
    (-> (.toString buf "base64")
        (s/replace #"=+$" ""))))

(defn base64->uid
  [base64str]
  (let [buf (js/Buffer.from base64str "base64")]
    (-> (.toString buf "utf-8")
        (s/reverse))))
