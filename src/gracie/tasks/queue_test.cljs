(ns gracie.tasks.queue-test
  (:require
    [promesa.core :as p]
    [framework.queue :as queue]))

(def requests (queue/create))
(queue/begin! requests)

(defn -main
  []
  (queue/enqueue
      requests
      (fn []
        (p/-> (p/delay 3000 "value-1")
              (println))))

  (queue/enqueue
    requests
    (fn []
      (p/-> (p/delay 3000 "value-2")
            (println))))

  (queue/enqueue
    requests
    (fn []
      (p/-> (p/delay 3000 "value-3")
            (println))))

  nil)
