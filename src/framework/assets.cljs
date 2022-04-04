(ns framework.assets
  (:require
   [clojure.string :as s]
   ["path" :as path]
   ["child_process" :as cp]))

(def basedir (atom "."))

(defn set-basedir!
  [base]
  (reset! basedir base))

(defn download-sync
  [dir url & [filename]]
  (println url)
  (let [base @basedir]
    (-> (.execFileSync cp "nbb"
                       #js ["./workers/download.cljs"
                            (js/JSON.stringify
                             (clj->js {:url url
                                       :root base
                                       :dir dir
                                       :filename filename}))]
                       #js {:encoding "utf-8"})
        (s/trim))))
