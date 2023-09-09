(ns framework.server.router2
  (:require [clojure.string :as s]))

(defn match-paths
  [paths route-paths]
  (if (not= (count paths) (count route-paths))
    nil
    (loop [i 0
           ret {:params {}}]
      (if (> i (dec (count route-paths)))
        ret
        (let [expected (nth route-paths i)
              actual   (nth paths i)]
          (cond
            ;; Dynamic var
            (s/starts-with? expected ":")
            (recur
              (inc i)
              (assoc-in ret
                        [:params (keyword (subs expected 1))]
                        actual))

            ;; Literal match
            (= expected actual)
            (recur
              (inc i)
              ret)

            ;; No match
            :else
            nil))))))


(defn path-matcher
  [current-path]
  (let [paths (s/split current-path #"/")]
    (fn [[route-paths view-fn :as route]]
      (let [result (match-paths paths route-paths)]
        (when result
          {:view-fn view-fn
           :params (:params result)})))))

(defn route-url
  [routes f]
  (let [routes (for [[route-path handler] routes]
                 [(s/split route-path #"/") handler])]
    (fn [req]
     (->> routes
          (keep (path-matcher (:path req)))
          (first)
          (f req)))))

(comment
  (match-paths
    ["/"]
    ["/"])

  ((path-matcher "/")
   [[] (fn [] nil)]))
