(ns gracie.tasks.generate-keypair
  (:require
    ["crypto" :as crypto]))


(def generate-key-pair-sync (.-generateKeyPairSync crypto))

(defn generate-private-key
  []
  (generate-key-pair-sync
    "ec" (clj->js {:namedCurve "secp256k1"
                   :privateKeyEncoding {:type "pkcs8"
                                        :format "pem"}})))

(defonce keypair (generate-private-key))
(defonce private-key (.createPrivateKey crypto (.-privateKey keypair)))

(defn -main
  []
  (println (.export private-key #js {:type "pkcs8"
                                     :format "pem"})))
